"""Deterministic FFmpeg-based video editor."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Optional, Union

from PIL import Image, ImageDraw, ImageFont

from ai_youtube.domain.models import EditManifest, ScenePlan


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}


class VideoEditingError(RuntimeError):
    """Raised when media validation or FFmpeg rendering fails."""


class FFmpegEditor:
    def __init__(
        self,
        config: dict[str, Any],
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
        ffmpeg_binary: str = "ffmpeg",
        ffprobe_binary: str = "ffprobe",
    ) -> None:
        self.config = config
        self.runner = runner
        self.ffmpeg_binary = ffmpeg_binary
        self.ffprobe_binary = ffprobe_binary

    def check_available(self) -> None:
        if shutil.which(self.ffmpeg_binary) is None:
            raise VideoEditingError(
                "FFmpeg를 찾을 수 없습니다. macOS에서는 'brew install ffmpeg'로 설치하세요."
            )
        if shutil.which(self.ffprobe_binary) is None:
            raise VideoEditingError("ffprobe를 찾을 수 없습니다. FFmpeg를 다시 설치하세요.")

    def probe_duration(self, media_path: Path) -> float:
        result = self.runner(
            [
                self.ffprobe_binary,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(media_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        try:
            duration = float(json.loads(result.stdout)["format"]["duration"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise VideoEditingError(f"미디어 길이를 확인할 수 없습니다: {media_path}") from exc
        if duration <= 0:
            raise VideoEditingError(f"미디어 길이가 올바르지 않습니다: {media_path}")
        return duration

    @staticmethod
    def _validate_files(scene_plan: ScenePlan, manifest: EditManifest) -> None:
        if not manifest.narration_path.is_file():
            raise FileNotFoundError(f"내레이션 파일이 없습니다: {manifest.narration_path}")
        if manifest.bgm_path and not manifest.bgm_path.is_file():
            raise FileNotFoundError(f"BGM 파일이 없습니다: {manifest.bgm_path}")

        media_by_scene = {item.scene_number: item for item in manifest.scenes}
        if len(media_by_scene) != len(manifest.scenes):
            raise VideoEditingError("매니페스트에 중복된 scene_number가 있습니다.")
        expected = {scene.scene_number for scene in scene_plan.scenes}
        if media_by_scene.keys() != expected:
            missing = sorted(expected - media_by_scene.keys())
            extra = sorted(media_by_scene.keys() - expected)
            raise VideoEditingError(f"Scene 미디어가 일치하지 않습니다. 누락={missing}, 추가={extra}")

        for item in manifest.scenes:
            if not item.media_path.is_file():
                raise FileNotFoundError(f"Scene 미디어가 없습니다: {item.media_path}")
            suffix = item.media_path.suffix.lower()
            if suffix not in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
                raise VideoEditingError(f"지원하지 않는 Scene 미디어 형식입니다: {suffix}")
            if item.sound_effect_path and not item.sound_effect_path.is_file():
                raise FileNotFoundError(f"효과음 파일이 없습니다: {item.sound_effect_path}")

    @staticmethod
    def _allocate_durations(scene_plan: ScenePlan, total_duration: float) -> list[float]:
        weights = [max(len(scene.narration.strip()), 1) for scene in scene_plan.scenes]
        total_weight = sum(weights)
        return [total_duration * weight / total_weight for weight in weights]

    @staticmethod
    def _srt_timestamp(seconds: float) -> str:
        milliseconds = max(0, round(seconds * 1000))
        hours, remainder = divmod(milliseconds, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        secs, millis = divmod(remainder, 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

    def _write_srt(
        self, scene_plan: ScenePlan, durations: list[float], path: Path
    ) -> None:
        cursor = 0.0
        blocks = []
        for index, (scene, duration) in enumerate(zip(scene_plan.scenes, durations), start=1):
            end = cursor + duration
            blocks.append(
                f"{index}\n{self._srt_timestamp(cursor)} --> {self._srt_timestamp(end)}\n"
                f"{scene.subtitle.strip()}\n"
            )
            cursor = end
        path.write_text("\n".join(blocks), encoding="utf-8")

    @staticmethod
    def _subtitle_font(
        font_size: int,
    ) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
        candidates = (
            Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        )
        for candidate in candidates:
            if candidate.is_file():
                return ImageFont.truetype(str(candidate), size=font_size)
        return ImageFont.load_default()

    def _write_subtitle_overlays(
        self,
        scene_plan: ScenePlan,
        width: int,
        height: int,
        work_dir: Path,
    ) -> list[Path]:
        style = self.config["subtitle"]
        font_size = max(int(style["font_size"]) * 2, 36)
        font = self._subtitle_font(font_size)
        margin_vertical = int(style["margin_vertical"])
        max_width = int(width * 0.86)
        draw_probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        overlays = []

        for scene in scene_plan.scenes:
            words = scene.subtitle.strip().split()
            lines: list[str] = []
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                box = draw_probe.textbbox((0, 0), candidate, font=font, stroke_width=2)
                if current and box[2] - box[0] > max_width:
                    lines.append(current)
                    current = word
                else:
                    current = candidate
            if current:
                lines.append(current)
            text = "\n".join(lines or [scene.subtitle.strip()])

            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            bbox = draw.multiline_textbbox(
                (0, 0), text, font=font, spacing=10, align="center", stroke_width=2
            )
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2
            y = height - margin_vertical - text_height
            padding_x, padding_y = 28, 18
            draw.rounded_rectangle(
                (
                    x - padding_x,
                    y - padding_y,
                    x + text_width + padding_x,
                    y + text_height + padding_y,
                ),
                radius=18,
                fill=(0, 0, 0, 150),
            )
            draw.multiline_text(
                (x, y),
                text,
                font=font,
                fill=(255, 255, 255, 255),
                spacing=10,
                align="center",
                stroke_width=2,
                stroke_fill=(0, 0, 0, 255),
            )
            path = work_dir / f"subtitle_{scene.scene_number:03d}.png"
            overlay.save(path, format="PNG")
            overlays.append(path)
        return overlays

    def _build_command(
        self,
        scene_plan: ScenePlan,
        manifest: EditManifest,
        output_path: Path,
        work_dir: Path,
        narration_duration: float,
    ) -> list[str]:
        width, height = (1080, 1920) if scene_plan.aspect_ratio == "9:16" else (1920, 1080)
        transition = self.config["transition"]
        transition_duration = float(transition["duration_seconds"])
        transition_type = str(transition["type"])
        fps = int(self.config["fps"])
        durations = self._allocate_durations(scene_plan, narration_duration)
        scene_media = {item.scene_number: item for item in manifest.scenes}
        subtitle_overlays = self._write_subtitle_overlays(
            scene_plan, width, height, work_dir
        )

        command = [self.ffmpeg_binary, "-y"]
        clip_durations = []
        for index, scene in enumerate(scene_plan.scenes):
            media = scene_media[scene.scene_number]
            clip_duration = durations[index] + (transition_duration if index < len(durations) - 1 else 0)
            clip_durations.append(clip_duration)
            if media.media_path.suffix.lower() in IMAGE_EXTENSIONS:
                command.extend(["-loop", "1", "-t", f"{clip_duration:.3f}", "-i", str(media.media_path)])
            else:
                command.extend(["-stream_loop", "-1", "-t", f"{clip_duration:.3f}", "-i", str(media.media_path)])

        scene_count = len(scene_plan.scenes)
        for index, subtitle_overlay in enumerate(subtitle_overlays):
            command.extend(
                ["-loop", "1", "-t", f"{clip_durations[index]:.3f}", "-i", str(subtitle_overlay)]
            )

        narration_index = scene_count * 2
        command.extend(["-i", str(manifest.narration_path)])
        bgm_index: Optional[int] = None
        if manifest.bgm_path:
            bgm_index = narration_index + 1
            command.extend(["-stream_loop", "-1", "-i", str(manifest.bgm_path)])

        sfx_indices: list[tuple[int, Any]] = []
        next_index = narration_index + 1 + (1 if manifest.bgm_path else 0)
        for scene in scene_plan.scenes:
            media = scene_media[scene.scene_number]
            if media.sound_effect_path:
                command.extend(["-i", str(media.sound_effect_path)])
                sfx_indices.append((next_index, media))
                next_index += 1

        filters = []
        for index, clip_duration in enumerate(clip_durations):
            filters.append(
                f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},fps={fps},trim=duration={clip_duration:.3f},"
                f"setpts=PTS-STARTPTS[base{index}]"
            )
            filters.append(
                f"[{scene_count + index}:v]format=rgba,fps={fps},"
                f"trim=duration={clip_duration:.3f},setpts=PTS-STARTPTS[sub{index}]"
            )
            filters.append(
                f"[base{index}][sub{index}]overlay=0:0:format=auto[v{index}]"
            )

        video_label = "v0"
        cumulative = durations[0]
        for index in range(1, len(scene_plan.scenes)):
            output_label = f"vx{index}"
            filters.append(
                f"[{video_label}][v{index}]xfade=transition={transition_type}:"
                f"duration={transition_duration:.3f}:offset={cumulative:.3f}[{output_label}]"
            )
            video_label = output_label
            cumulative += durations[index]

        filters.append(f"[{video_label}]null[videoout]")

        audio = self.config["audio"]
        filters.append(
            f"[{narration_index}:a]volume={float(audio['narration_volume'])},"
            f"atrim=duration={narration_duration:.3f},asetpts=PTS-STARTPTS[narration]"
        )
        audio_labels = ["narration"]
        if bgm_index is not None:
            filters.append(
                f"[{bgm_index}:a]volume={float(audio['bgm_volume'])},"
                f"atrim=duration={narration_duration:.3f},asetpts=PTS-STARTPTS[bgm]"
            )
            audio_labels.append("bgm")

        scene_starts = []
        cursor = 0.0
        for duration in durations:
            scene_starts.append(cursor)
            cursor += duration
        for position, (input_index, media) in enumerate(sfx_indices):
            scene_position = next(
                idx for idx, item in enumerate(scene_plan.scenes) if item.scene_number == media.scene_number
            )
            delay_ms = round((scene_starts[scene_position] + media.sound_effect_offset_seconds) * 1000)
            label = f"sfx{position}"
            filters.append(
                f"[{input_index}:a]volume={float(audio['sound_effect_volume'])},"
                f"adelay={delay_ms}|{delay_ms}[{label}]"
            )
            audio_labels.append(label)

        if len(audio_labels) == 1:
            filters.append("[narration]anull[audioout]")
        else:
            inputs = "".join(f"[{label}]" for label in audio_labels)
            filters.append(
                f"{inputs}amix=inputs={len(audio_labels)}:duration=first:dropout_transition=2[audioout]"
            )

        filter_script = work_dir / "filters.txt"
        filter_script.write_text(";\n".join(filters), encoding="utf-8")
        command.extend(
            [
                "-filter_complex_script",
                str(filter_script),
                "-map",
                "[videoout]",
                "-map",
                "[audioout]",
                "-c:v",
                str(self.config["video_codec"]),
                "-pix_fmt",
                str(self.config["pixel_format"]),
                "-c:a",
                str(self.config["audio_codec"]),
                "-b:a",
                str(self.config["audio_bitrate"]),
                "-movflags",
                "+faststart",
                "-t",
                f"{narration_duration:.3f}",
                str(output_path),
            ]
        )
        return command

    def render(
        self, scene_plan: ScenePlan, manifest: EditManifest, output_path: Path
    ) -> Path:
        self.check_available()
        self._validate_files(scene_plan, manifest)
        if output_path.suffix.lower() != ".mp4":
            raise VideoEditingError("출력 파일 확장자는 .mp4여야 합니다.")
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        narration_duration = self.probe_duration(manifest.narration_path)

        with tempfile.TemporaryDirectory(prefix="ai-youtube-edit-") as temporary:
            work_dir = Path(temporary)
            command = self._build_command(
                scene_plan, manifest, output_path, work_dir, narration_duration
            )
            try:
                self.runner(command, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as exc:
                output_path.unlink(missing_ok=True)
                details = (exc.stderr or exc.stdout or "FFmpeg 오류").strip()[-2000:]
                raise VideoEditingError(f"FFmpeg 렌더링에 실패했습니다: {details}") from exc

        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise VideoEditingError("렌더링 결과 파일이 생성되지 않았습니다.")
        return output_path

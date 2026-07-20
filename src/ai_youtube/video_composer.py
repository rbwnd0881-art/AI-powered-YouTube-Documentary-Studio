"""Minimal FFmpeg composer for ordered still images."""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable


logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class VideoCompositionError(RuntimeError):
    """Raised when image composition cannot produce a valid MP4."""


class VideoComposer:
    """Compose filename-ordered images into a silent vertical MP4."""

    def __init__(
        self,
        config: dict[str, Any],
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
        ffmpeg_binary: str = "ffmpeg",
    ) -> None:
        self.width = int(config.get("width", 1080))
        self.height = int(config.get("height", 1920))
        self.image_duration_seconds = float(config["image_duration_seconds"])
        self.fps = int(config["fps"])
        self.runner = runner
        self.ffmpeg_binary = ffmpeg_binary
        if self.image_duration_seconds <= 0:
            raise ValueError("image_duration_seconds는 0보다 커야 합니다.")
        if self.fps <= 0:
            raise ValueError("fps는 0보다 커야 합니다.")

    @staticmethod
    def list_images(image_dir: Path) -> list[Path]:
        """Return supported image files in deterministic filename order."""
        image_dir = image_dir.resolve()
        if not image_dir.is_dir():
            raise FileNotFoundError(f"이미지 폴더를 찾을 수 없습니다: {image_dir}")
        images = sorted(
            (
                path
                for path in image_dir.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            ),
            key=lambda path: path.name,
        )
        if not images:
            raise VideoCompositionError(f"이미지 파일이 없습니다: {image_dir}")
        return images

    def _build_command(self, images: list[Path], output_path: Path) -> list[str]:
        command = [self.ffmpeg_binary, "-y"]
        for image in images:
            command.extend(
                [
                    "-loop",
                    "1",
                    "-t",
                    f"{self.image_duration_seconds:.3f}",
                    "-i",
                    str(image),
                ]
            )

        filters = []
        for index in range(len(images)):
            filters.append(
                f"[{index}:v]scale={self.width}:{self.height}:"
                "force_original_aspect_ratio=increase,"
                f"crop={self.width}:{self.height},fps={self.fps},"
                f"trim=duration={self.image_duration_seconds:.3f},"
                f"setpts=PTS-STARTPTS[v{index}]"
            )
        inputs = "".join(f"[v{index}]" for index in range(len(images)))
        filters.append(f"{inputs}concat=n={len(images)}:v=1:a=0[videoout]")

        command.extend(
            [
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[videoout]",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-an",
                "-movflags",
                "+faststart",
                str(output_path),
            ]
        )
        return command

    def compose(
        self,
        image_dir: Path,
        output_dir: Path,
        output_filename: str = "composed.mp4",
    ) -> Path:
        """Create one MP4 and return its absolute path."""
        if Path(output_filename).name != output_filename or not output_filename.lower().endswith(
            ".mp4"
        ):
            raise ValueError("output_filename은 경로가 아닌 .mp4 파일명이어야 합니다.")
        if shutil.which(self.ffmpeg_binary) is None:
            raise VideoCompositionError("FFmpeg를 찾을 수 없습니다.")

        images = self.list_images(image_dir)
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_filename
        logger.info("이미지 %s장을 MP4로 합성합니다: %s", len(images), output_path)

        try:
            self.runner(
                self._build_command(images, output_path),
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            output_path.unlink(missing_ok=True)
            details = (exc.stderr or exc.stdout or "FFmpeg 오류").strip()[-2000:]
            raise VideoCompositionError(f"영상 합성에 실패했습니다: {details}") from exc

        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise VideoCompositionError("MP4 결과 파일이 생성되지 않았습니다.")
        logger.info("MP4 합성이 완료되었습니다: %s", output_path)
        return output_path

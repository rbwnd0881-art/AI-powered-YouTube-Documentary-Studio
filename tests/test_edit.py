import json
import subprocess
from pathlib import Path

import ai_youtube.providers.ffmpeg_provider as ffmpeg_module
from ai_youtube.config import load_app_config
from ai_youtube.domain.models import EditManifest, ScenePlan
from ai_youtube.pipeline.stages.edit import YoutubeEditService
from ai_youtube.providers.ffmpeg_provider import FFmpegEditor


SCENE_PLAN = {
    "topic": "꿈",
    "title": "꿈을 잊는 이유",
    "aspect_ratio": "9:16",
    "scenes": [
        {
            "scene_number": 1,
            "source_id": "hook",
            "narration": "꿈은 왜 사라질까요?",
            "image_prompt": "dream particles",
            "video_prompt": "slow push in",
            "subtitle": "꿈은 왜 사라질까",
        },
        {
            "scene_number": 2,
            "source_id": "body_1",
            "narration": "뇌가 장기 기억으로 저장하지 않기 때문입니다.",
            "image_prompt": "glowing brain",
            "video_prompt": "brain glow fades",
            "subtitle": "장기 기억에 저장되지 않는다",
        },
    ],
}


def test_load_manifest_resolves_relative_paths(tmp_path):
    manifest_path = tmp_path / "edit-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "narration_path": "voice.mp3",
                "scenes": [
                    {"scene_number": 1, "media_path": "media/scene_001.png"}
                ],
            }
        ),
        encoding="utf-8",
    )
    result = YoutubeEditService.load_manifest(manifest_path)
    assert result.narration_path == (tmp_path / "voice.mp3").resolve()
    assert result.scenes[0].media_path == (tmp_path / "media/scene_001.png").resolve()


def test_allocate_durations_matches_narration_length():
    plan = ScenePlan.model_validate(SCENE_PLAN)
    durations = FFmpegEditor._allocate_durations(plan, 12.5)
    assert len(durations) == 2
    assert sum(durations) == 12.5
    assert durations[1] > durations[0]


def test_render_builds_ffmpeg_pipeline(tmp_path, monkeypatch):
    voice = tmp_path / "voice.mp3"
    image = tmp_path / "scene_001.png"
    video = tmp_path / "scene_002.mp4"
    for path in (voice, image, video):
        path.write_bytes(b"fake")

    plan = ScenePlan.model_validate(SCENE_PLAN)
    manifest = EditManifest.model_validate(
        {
            "narration_path": voice,
            "scenes": [
                {"scene_number": 1, "media_path": image},
                {"scene_number": 2, "media_path": video},
            ],
        }
    )
    commands = []

    def fake_runner(command, **kwargs):
        commands.append(command)
        if command[0] == "ffprobe":
            return subprocess.CompletedProcess(
                command, 0, stdout='{"format":{"duration":"10.0"}}', stderr=""
            )
        Path(command[-1]).write_bytes(b"fake-mp4")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(ffmpeg_module.shutil, "which", lambda binary: f"/usr/bin/{binary}")
    output = FFmpegEditor(load_app_config()["editing"], runner=fake_runner).render(
        scene_plan=plan,
        manifest=manifest,
        output_path=tmp_path / "final.mp4",
    )
    assert output.read_bytes() == b"fake-mp4"
    ffmpeg_command = commands[1]
    assert "-filter_complex_script" in ffmpeg_command
    assert "-loop" in ffmpeg_command
    assert "-stream_loop" in ffmpeg_command


def test_subtitle_overlays_do_not_require_libass(tmp_path):
    plan = ScenePlan.model_validate(SCENE_PLAN)
    editor = FFmpegEditor(load_app_config()["editing"])
    overlays = editor._write_subtitle_overlays(plan, 1080, 1920, tmp_path)

    assert len(overlays) == 2
    assert all(path.is_file() and path.stat().st_size > 0 for path in overlays)

import subprocess
from pathlib import Path

import pytest

import ai_youtube.video_composer as composer_module
from ai_youtube.video_composer import VideoComposer


def config(duration=3.0, fps=30):
    return {
        "width": 1080,
        "height": 1920,
        "image_duration_seconds": duration,
        "fps": fps,
    }


def test_list_images_sorts_supported_files_by_filename(tmp_path):
    for name in ("scene_010.png", "scene_002.jpg", "scene_001.webp", "notes.txt"):
        (tmp_path / name).write_bytes(b"image")

    images = VideoComposer.list_images(tmp_path)

    assert [path.name for path in images] == [
        "scene_001.webp",
        "scene_002.jpg",
        "scene_010.png",
    ]


def test_compose_creates_configured_output_and_command(tmp_path, monkeypatch):
    image_dir = tmp_path / "images"
    output_dir = tmp_path / "output"
    image_dir.mkdir()
    for name in ("scene_002.png", "scene_001.png"):
        (image_dir / name).write_bytes(b"image")
    commands = []

    def fake_runner(command, **kwargs):
        commands.append(command)
        Path(command[-1]).write_bytes(b"mp4")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(composer_module.shutil, "which", lambda _: "/usr/bin/ffmpeg")
    result = VideoComposer(config(duration=1.25, fps=24), runner=fake_runner).compose(
        image_dir, output_dir, "short.mp4"
    )

    assert result == (output_dir / "short.mp4").resolve()
    assert result.read_bytes() == b"mp4"
    command = commands[0]
    first_image = command.index(str((image_dir / "scene_001.png").resolve()))
    second_image = command.index(str((image_dir / "scene_002.png").resolve()))
    assert first_image < second_image
    assert command.count("1.250") == 2
    assert "fps=24" in command[command.index("-filter_complex") + 1]
    assert "scale=1080:1920" in command[command.index("-filter_complex") + 1]


@pytest.mark.parametrize(
    "bad_config",
    [config(duration=0), config(fps=0)],
)
def test_composer_rejects_invalid_timing_configuration(bad_config):
    with pytest.raises(ValueError):
        VideoComposer(bad_config)

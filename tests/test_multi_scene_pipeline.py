import pytest

from ai_youtube.pipeline.multi_scene import (
    MultiSceneImagePipeline,
    SceneImageGenerationError,
)
from ai_youtube.providers.placeholder_image_provider import PlaceholderImageProvider


PROMPTS = ["hook", "first explanation", "second explanation", "conclusion"]


class FakeImageProvider:
    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at

    def generate(self, prompt, output_path, width, height, label=""):
        scene_number = len(self.calls) + 1
        self.calls.append((prompt, output_path, width, height, label))
        if scene_number == self.fail_at:
            raise RuntimeError("image failure")
        output_path.write_bytes(f"scene-{scene_number}".encode())
        return output_path


class FakeComposer:
    def __init__(self):
        self.calls = []

    def compose(self, image_dir, output_dir, output_filename="composed.mp4"):
        images = sorted(image_dir.glob("scene_*.png"))
        self.calls.append((image_dir, output_dir, output_filename, images))
        output = output_dir / output_filename
        output.write_bytes(b"mp4")
        return output


def test_pipeline_generates_four_ordered_images_and_video(tmp_path):
    provider = FakeImageProvider()
    composer = FakeComposer()
    pipeline = MultiSceneImagePipeline(provider, composer)

    result = pipeline.run("Octopus hearts", PROMPTS, tmp_path / "job")

    expected_names = [f"scene_{index:03d}.png" for index in range(1, 5)]
    assert len(provider.calls) == 4
    assert [call[0] for call in provider.calls] == PROMPTS
    assert [path.name for path in result.image_paths] == expected_names
    assert [path.name for path in composer.calls[0][3]] == expected_names
    assert result.video_path == (tmp_path / "job" / "shorts-m3.mp4").resolve()
    assert result.video_path.is_file()


def test_pipeline_stops_at_failed_scene_and_does_not_compose(tmp_path):
    provider = FakeImageProvider(fail_at=3)
    composer = FakeComposer()
    job_dir = tmp_path / "failed-job"
    pipeline = MultiSceneImagePipeline(provider, composer)

    with pytest.raises(SceneImageGenerationError) as error:
        pipeline.run("Octopus hearts", PROMPTS, job_dir)

    assert error.value.scene_number == 3
    assert len(provider.calls) == 3
    assert [path.name for path in sorted(job_dir.glob("*.png"))] == [
        "scene_001.png",
        "scene_002.png",
    ]
    assert composer.calls == []
    assert not (job_dir / "shorts-m3.mp4").exists()


def test_pipeline_supports_placeholder_provider(tmp_path):
    composer = FakeComposer()
    job_dir = tmp_path / "placeholder-job"
    pipeline = MultiSceneImagePipeline(
        PlaceholderImageProvider(), composer, width=64, height=96
    )

    result = pipeline.run("Placeholder", PROMPTS, job_dir)

    assert len(result.image_paths) == 4
    assert all(path.is_file() for path in result.image_paths)
    assert result.video_path.is_file()


def test_pipeline_refuses_nonempty_job_directory(tmp_path):
    job_dir = tmp_path / "existing-job"
    job_dir.mkdir()
    (job_dir / "existing.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        MultiSceneImagePipeline(FakeImageProvider(), FakeComposer()).run(
            "Octopus hearts", PROMPTS, job_dir
        )

    assert (job_dir / "existing.txt").read_text(encoding="utf-8") == "keep"

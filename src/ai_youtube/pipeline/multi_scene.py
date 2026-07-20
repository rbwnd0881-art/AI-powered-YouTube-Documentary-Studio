"""Minimal multi-scene image-to-video pipeline."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from ai_youtube.providers.base import VisualProvider


logger = logging.getLogger(__name__)


class Composer(Protocol):
    def compose(
        self,
        image_dir: Path,
        output_dir: Path,
        output_filename: str = "composed.mp4",
    ) -> Path: ...


class SceneImageGenerationError(RuntimeError):
    """Identify the scene that stopped the M3 pipeline."""

    def __init__(self, scene_number: int) -> None:
        self.scene_number = scene_number
        super().__init__(f"Scene {scene_number} 이미지 생성에 실패했습니다.")


@dataclass(frozen=True)
class MultiSceneResult:
    topic: str
    image_paths: tuple[Path, ...]
    video_path: Path


class MultiSceneImagePipeline:
    """Generate ordered images and compose them only after all scenes succeed."""

    def __init__(
        self,
        visual_provider: VisualProvider,
        video_composer: Composer,
        width: int = 1080,
        height: int = 1920,
    ) -> None:
        self.visual_provider = visual_provider
        self.video_composer = video_composer
        self.width = width
        self.height = height

    def run(
        self,
        topic: str,
        scene_prompts: Sequence[str],
        job_dir: Path,
        output_filename: str = "shorts-m3.mp4",
    ) -> MultiSceneResult:
        clean_topic = topic.strip()
        prompts = [prompt.strip() for prompt in scene_prompts]
        if not clean_topic:
            raise ValueError("주제를 한 글자 이상 입력하세요.")
        if not prompts or any(not prompt for prompt in prompts):
            raise ValueError("모든 Scene 프롬프트가 필요합니다.")

        job_dir = job_dir.resolve()
        if job_dir.exists() and any(job_dir.iterdir()):
            raise FileExistsError(f"비어 있지 않은 Job 폴더는 사용할 수 없습니다: {job_dir}")
        job_dir.mkdir(parents=True, exist_ok=True)

        image_paths = []
        for scene_number, prompt in enumerate(prompts, start=1):
            image_path = job_dir / f"scene_{scene_number:03d}.png"
            logger.info("Scene %s 이미지를 생성합니다.", scene_number)
            try:
                generated_path = self.visual_provider.generate(
                    prompt=prompt,
                    output_path=image_path,
                    width=self.width,
                    height=self.height,
                    label=f"SCENE {scene_number}",
                )
            except Exception as exc:
                logger.error("Scene %s 이미지 생성에 실패했습니다.", scene_number)
                raise SceneImageGenerationError(scene_number) from exc
            image_paths.append(generated_path.resolve())

        video_path = self.video_composer.compose(
            image_dir=job_dir,
            output_dir=job_dir,
            output_filename=output_filename,
        )
        return MultiSceneResult(
            topic=clean_topic,
            image_paths=tuple(image_paths),
            video_path=video_path.resolve(),
        )

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ScriptScene(BaseModel):
    scene_number: int = Field(ge=1)
    narration: str = Field(min_length=1)
    visual_prompt: str = Field(min_length=1)
    on_screen_text: str = ""


class YoutubeScript(BaseModel):
    topic: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=100)
    hook: str = Field(min_length=1)
    scenes: list[ScriptScene] = Field(min_length=1)
    outro: str = Field(min_length=1)
    description: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)

    def narration_text(self) -> str:
        parts = [self.hook]
        parts.extend(scene.narration for scene in self.scenes)
        parts.append(self.outro)
        return "\n\n".join(part.strip() for part in parts if part.strip())


class GeneratedSceneAssets(BaseModel):
    source_id: str = Field(min_length=1)
    image_prompt: str = Field(min_length=1)
    video_prompt: str = Field(min_length=1)
    subtitle: str = Field(min_length=1)


class GeneratedSceneAssetsPlan(BaseModel):
    scenes: list[GeneratedSceneAssets] = Field(min_length=1)


class ProductionScene(BaseModel):
    scene_number: int = Field(ge=1)
    source_id: str = Field(min_length=1)
    narration: str = Field(min_length=1)
    image_prompt: str = Field(min_length=1)
    video_prompt: str = Field(min_length=1)
    subtitle: str = Field(min_length=1)


class ScenePlan(BaseModel):
    topic: str = Field(min_length=1)
    title: str = Field(min_length=1)
    aspect_ratio: str = Field(min_length=1)
    scenes: list[ProductionScene] = Field(min_length=1)


class SceneMedia(BaseModel):
    scene_number: int = Field(ge=1)
    media_path: Path
    sound_effect_path: Optional[Path] = None
    sound_effect_offset_seconds: float = Field(default=0.0, ge=0)


class EditManifest(BaseModel):
    narration_path: Path
    bgm_path: Optional[Path] = None
    scenes: list[SceneMedia] = Field(min_length=1)


class PublishingMetadata(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=5000)
    tags: list[str] = Field(default_factory=list)
    thumbnail_text: str = Field(min_length=1, max_length=40)


class YoutubeUploadResult(BaseModel):
    video_id: str = Field(min_length=1)
    url: str = Field(min_length=1)
    privacy: str = Field(min_length=1)
    thumbnail_uploaded: bool


@dataclass(frozen=True)
class VideoJob:
    id: str
    channel_id: str
    idea: str
    status: str
    created_at: str

    @classmethod
    def create(cls, channel_id: str, idea: str) -> "VideoJob":
        return cls(
            id=str(uuid4()),
            channel_id=channel_id,
            idea=idea,
            status="planned",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

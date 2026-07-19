import json
from pathlib import Path
from typing import Optional

from ai_youtube.domain.models import EditManifest, ScenePlan


class YoutubeEditService:
    @staticmethod
    def _read_json(path: Path) -> dict:
        if not path.is_file():
            raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {path}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"JSON 파일을 읽을 수 없습니다: {path}: {exc}") from exc

    @classmethod
    def load_scene_plan(cls, path: Path) -> ScenePlan:
        return ScenePlan.model_validate(cls._read_json(path))

    @classmethod
    def load_manifest(cls, path: Path) -> EditManifest:
        manifest = EditManifest.model_validate(cls._read_json(path))
        base_dir = path.resolve().parent

        def resolve(media_path: Optional[Path]) -> Optional[Path]:
            if media_path is None or media_path.is_absolute():
                return media_path
            return (base_dir / media_path).resolve()

        return manifest.model_copy(
            update={
                "narration_path": resolve(manifest.narration_path),
                "bgm_path": resolve(manifest.bgm_path),
                "scenes": [
                    item.model_copy(
                        update={
                            "media_path": resolve(item.media_path),
                            "sound_effect_path": resolve(item.sound_effect_path),
                        }
                    )
                    for item in manifest.scenes
                ],
            }
        )

"""Checkpointed end-to-end MVP video pipeline."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_youtube.domain.models import EditManifest, SceneMedia, ScenePlan, VideoJob, YoutubeScript
from ai_youtube.pipeline.stages.scenes import YoutubeSceneService
from ai_youtube.pipeline.stages.script import YoutubeScriptService
from ai_youtube.pipeline.stages.voice import YoutubeVoiceService
from ai_youtube.providers.base import SpeechProvider, TextProvider, VideoEditor, VisualProvider


STAGES = [
    "script",
    "storyboard",
    "voice",
    "visuals",
    "edit",
    "thumbnail",
    "quality_check",
    "upload",
]


def create_job_plan(channel_config: dict[str, Any], idea: str) -> dict[str, Any]:
    channel_id = channel_config["channel"]["id"]
    job = VideoJob.create(channel_id=channel_id, idea=idea)
    return {"job": job.to_dict(), "stages": STAGES}


class MvpPipeline:
    """Run the MVP stages while reusing valid artifacts from prior attempts."""

    STAGES = ("script", "scenes", "voice", "images", "edit")

    def __init__(
        self,
        text_provider: TextProvider,
        speech_provider: SpeechProvider,
        visual_provider: VisualProvider,
        editor: VideoEditor,
    ) -> None:
        self.script_service = YoutubeScriptService(text_provider)
        self.scene_service = YoutubeSceneService(text_provider)
        self.voice_service = YoutubeVoiceService(speech_provider)
        self.visual_provider = visual_provider
        self.editor = editor

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(path)

    @staticmethod
    def _read_model(path: Path, model_type: Any) -> Any:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))

    @classmethod
    def _new_state(cls, topic: str, channel_id: str) -> dict[str, Any]:
        return {
            "topic": topic,
            "channel_id": channel_id,
            "status": "running",
            "current_stage": None,
            "completed_stages": [],
            "error": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def run(
        self,
        topic: str,
        job_dir: Path,
        channel_config: dict[str, Any],
        app_config: dict[str, Any],
    ) -> Path:
        clean_topic = topic.strip()
        if not clean_topic:
            raise ValueError("주제를 한 글자 이상 입력하세요.")
        job_dir = job_dir.resolve()
        job_dir.mkdir(parents=True, exist_ok=True)
        state_path = job_dir / "state.json"
        channel_id = str(channel_config["channel"]["id"])
        state = self._new_state(clean_topic, channel_id)
        if state_path.is_file():
            saved = json.loads(state_path.read_text(encoding="utf-8"))
            if saved.get("topic") != clean_topic or saved.get("channel_id") != channel_id:
                raise ValueError("기존 작업 폴더의 주제 또는 채널이 현재 요청과 다릅니다.")
            state.update(saved)
            state.update({"status": "running", "error": None})

        def mark(stage: str, completed: bool = False) -> None:
            state["current_stage"] = stage
            if completed and stage not in state["completed_stages"]:
                state["completed_stages"].append(stage)
            state["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write_json(state_path, state)

        try:
            script_path = job_dir / "script.json"
            mark("script")
            if script_path.is_file():
                script = self._read_model(script_path, YoutubeScript)
            else:
                script = self.script_service.generate(clean_topic, channel_config)
                self._write_json(script_path, script.model_dump(mode="json"))
            mark("script", completed=True)

            scenes_path = job_dir / "scenes.json"
            mark("scenes")
            if scenes_path.is_file():
                scenes = self._read_model(scenes_path, ScenePlan)
            else:
                scenes = self.scene_service.generate(
                    script, channel_config, app_config["scene_generation"]
                )
                self._write_json(scenes_path, scenes.model_dump(mode="json"))
            mark("scenes", completed=True)

            speech_config = app_config["speech_generation"]
            voice_path = job_dir / f"voice.{speech_config['response_format']}"
            mark("voice")
            if not voice_path.is_file() or voice_path.stat().st_size == 0:
                self.voice_service.generate(
                    script, voice_path, channel_config, speech_config
                )
            mark("voice", completed=True)

            shorts = channel_config["content"]["formats"]["shorts"]
            width, height = (int(value) for value in shorts["resolution"])
            media_dir = job_dir / "media"
            media_items = []
            mark("images")
            for scene in scenes.scenes:
                image_path = media_dir / f"scene_{scene.scene_number:03d}.png"
                if not image_path.is_file() or image_path.stat().st_size == 0:
                    self.visual_provider.generate(
                        prompt=scene.image_prompt,
                        output_path=image_path,
                        width=width,
                        height=height,
                        label=f"SCENE {scene.scene_number}",
                    )
                media_items.append(
                    SceneMedia(scene_number=scene.scene_number, media_path=image_path)
                )
            mark("images", completed=True)

            manifest = EditManifest(narration_path=voice_path, scenes=media_items)
            manifest_path = job_dir / "edit-manifest.json"
            self._write_json(manifest_path, manifest.model_dump(mode="json"))
            output_path = job_dir / "final.mp4"
            mark("edit")
            if not output_path.is_file() or output_path.stat().st_size == 0:
                self.editor.render(scenes, manifest, output_path)
            mark("edit", completed=True)

            state.update(
                {
                    "status": "completed",
                    "current_stage": None,
                    "output": str(output_path),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            self._write_json(state_path, state)
            return output_path
        except Exception as exc:
            state.update(
                {
                    "status": "failed",
                    "error": str(exc),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            self._write_json(state_path, state)
            raise

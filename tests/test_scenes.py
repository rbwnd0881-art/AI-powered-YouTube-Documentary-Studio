import json

import pytest

from ai_youtube.domain.models import GeneratedSceneAssetsPlan, YoutubeScript
from ai_youtube.pipeline.stages.scenes import YoutubeSceneService


SCRIPT_DATA = {
    "topic": "꿈",
    "title": "꿈을 잊는 이유",
    "hook": "꿈이 순식간에 사라지는 이유가 있습니다.",
    "scenes": [
        {
            "scene_number": 1,
            "narration": "뇌는 꿈을 장기 기억으로 잘 저장하지 않습니다.",
            "visual_prompt": "sleeping person and glowing brain",
            "on_screen_text": "꿈은 왜 사라질까",
        }
    ],
    "outro": "다음 꿈은 바로 기록해 보세요.",
    "description": "꿈에 대한 설명",
    "tags": ["꿈"],
}


class FakeSceneProvider:
    def generate_structured(self, system_prompt, user_prompt, output_type):
        assert output_type is GeneratedSceneAssetsPlan
        return output_type(
            scenes=[
                {
                    "source_id": "hook",
                    "image_prompt": "Dream dissolving into light, vertical composition",
                    "video_prompt": "Dream particles drift away, slow push-in camera",
                    "subtitle": "꿈이 사라지는 이유",
                },
                {
                    "source_id": "body_1",
                    "image_prompt": "Glowing brain beside a sleeping person",
                    "video_prompt": "Brain glow fades, gentle orbit camera",
                    "subtitle": "장기 기억에 저장되지 않는다",
                },
                {
                    "source_id": "outro",
                    "image_prompt": "Hand writing a dream journal at sunrise",
                    "video_prompt": "Hand writes in journal, slow overhead camera",
                    "subtitle": "일어나자마자 기록하세요",
                },
            ]
        )


def scene_config():
    return {
        "visual_style": "cinematic illustration",
        "image_prompt_language": "en",
        "video_prompt_language": "en",
        "subtitle_language": "ko-KR",
        "max_subtitle_characters": 45,
    }


def channel_config():
    return {"content": {"formats": {"shorts": {"aspect_ratio": "9:16"}}}}


def test_scene_service_preserves_source_narration():
    script = YoutubeScript.model_validate(SCRIPT_DATA)
    result = YoutubeSceneService(FakeSceneProvider()).generate(
        script, channel_config(), scene_config()
    )
    assert len(result.scenes) == 3
    assert result.scenes[1].narration == SCRIPT_DATA["scenes"][0]["narration"]
    assert result.scenes[1].video_prompt.startswith("Brain glow")
    assert result.aspect_ratio == "9:16"


def test_scene_service_loads_json(tmp_path):
    path = tmp_path / "script.json"
    path.write_text(json.dumps(SCRIPT_DATA, ensure_ascii=False), encoding="utf-8")
    assert YoutubeSceneService.load_script(path).topic == "꿈"


class MissingSceneProvider:
    def generate_structured(self, system_prompt, user_prompt, output_type):
        return output_type(
            scenes=[
                {
                    "source_id": "hook",
                    "image_prompt": "image",
                    "video_prompt": "video",
                    "subtitle": "자막",
                }
            ]
        )


def test_scene_service_rejects_missing_source_id():
    script = YoutubeScript.model_validate(SCRIPT_DATA)
    with pytest.raises(ValueError, match="source_id"):
        YoutubeSceneService(MissingSceneProvider()).generate(
            script, channel_config(), scene_config()
        )

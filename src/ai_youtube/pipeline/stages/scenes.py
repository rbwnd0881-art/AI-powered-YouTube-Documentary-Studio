import json
from pathlib import Path
from typing import Any

from ai_youtube.domain.models import (
    GeneratedSceneAssetsPlan,
    ProductionScene,
    ScenePlan,
    YoutubeScript,
)
from ai_youtube.providers.base import TextProvider


class YoutubeSceneService:
    def __init__(self, provider: TextProvider) -> None:
        self.provider = provider

    @staticmethod
    def load_script(script_path: Path) -> YoutubeScript:
        if not script_path.is_file():
            raise FileNotFoundError(f"대본 파일을 찾을 수 없습니다: {script_path}")
        try:
            data = json.loads(script_path.read_text(encoding="utf-8"))
            return YoutubeScript.model_validate(data)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"대본 JSON 파일을 읽을 수 없습니다: {exc}") from exc

    @staticmethod
    def _source_segments(script: YoutubeScript) -> list[dict[str, str]]:
        segments = [{"source_id": "hook", "narration": script.hook}]
        segments.extend(
            {
                "source_id": f"body_{scene.scene_number}",
                "narration": scene.narration,
                "existing_image_prompt": scene.visual_prompt,
                "existing_on_screen_text": scene.on_screen_text,
            }
            for scene in script.scenes
        )
        segments.append({"source_id": "outro", "narration": script.outro})
        return segments

    def generate(
        self,
        script: YoutubeScript,
        channel_config: dict[str, Any],
        scene_config: dict[str, Any],
    ) -> ScenePlan:
        segments = self._source_segments(script)
        shorts_config = channel_config["content"]["formats"]["shorts"]
        aspect_ratio = str(shorts_config["aspect_ratio"])
        max_subtitle_characters = int(scene_config["max_subtitle_characters"])

        system_prompt = (
            "당신은 얼굴 없는 YouTube Shorts의 비주얼 디렉터다. "
            "주어진 각 source_id를 정확히 한 번씩 유지한다. 장면을 추가, 삭제, 병합하지 않는다. "
            "image_prompt는 정지 이미지의 구도와 피사체를, video_prompt는 움직임과 카메라 동작을 "
            "구체적으로 설명한다. 로고, 워터마크, 화면 속 글자를 생성하지 않는다."
        )
        user_prompt = f"""
아래 고정 장면 각각에 제작 정보를 생성하라.

영상 주제: {script.topic}
화면 비율: {aspect_ratio}
공통 비주얼 스타일: {scene_config['visual_style']}
이미지 프롬프트 언어: {scene_config['image_prompt_language']}
영상 프롬프트 언어: {scene_config['video_prompt_language']}
자막 언어: {scene_config['subtitle_language']}
자막 최대 길이: {max_subtitle_characters}자

규칙:
- 입력의 source_id를 변경하지 말 것
- 모든 source_id를 정확히 한 번 포함할 것
- 이미지와 영상 프롬프트는 같은 피사체, 배경, 색감을 유지할 것
- video_prompt에는 피사체 움직임, 카메라 움직임, 분위기를 포함할 것
- 자막은 해당 내레이션의 핵심을 자연스럽게 압축할 것
- 자막에 이모지, 해시태그, 따옴표를 넣지 말 것

고정 장면 JSON:
{json.dumps(segments, ensure_ascii=False, indent=2)}
""".strip()

        generated = self.provider.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_type=GeneratedSceneAssetsPlan,
        )

        source_by_id = {item["source_id"]: item["narration"] for item in segments}
        generated_by_id = {scene.source_id: scene for scene in generated.scenes}
        if len(generated_by_id) != len(generated.scenes):
            raise ValueError("OpenAI 결과에 중복된 source_id가 있습니다.")
        if generated_by_id.keys() != source_by_id.keys():
            missing = sorted(source_by_id.keys() - generated_by_id.keys())
            extra = sorted(generated_by_id.keys() - source_by_id.keys())
            raise ValueError(f"Scene source_id가 일치하지 않습니다. 누락={missing}, 추가={extra}")

        production_scenes = []
        for number, source in enumerate(segments, start=1):
            assets = generated_by_id[source["source_id"]]
            if len(assets.subtitle) > max_subtitle_characters:
                raise ValueError(
                    f"{assets.source_id} 자막이 {max_subtitle_characters}자를 초과했습니다."
                )
            production_scenes.append(
                ProductionScene(
                    scene_number=number,
                    source_id=assets.source_id,
                    narration=source["narration"],
                    image_prompt=assets.image_prompt,
                    video_prompt=assets.video_prompt,
                    subtitle=assets.subtitle,
                )
            )

        return ScenePlan(
            topic=script.topic,
            title=script.title,
            aspect_ratio=aspect_ratio,
            scenes=production_scenes,
        )

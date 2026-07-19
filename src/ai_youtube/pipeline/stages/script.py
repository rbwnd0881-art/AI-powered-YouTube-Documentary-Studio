from typing import Any, Optional

from ai_youtube.domain.models import YoutubeScript
from ai_youtube.providers.base import TextProvider


class YoutubeScriptService:
    def __init__(self, provider: TextProvider) -> None:
        self.provider = provider

    def generate(
        self,
        topic: str,
        channel_config: dict[str, Any],
        duration_seconds: Optional[int] = None,
    ) -> YoutubeScript:
        clean_topic = topic.strip()
        if not clean_topic:
            raise ValueError("주제를 한 글자 이상 입력하세요.")

        channel = channel_config["channel"]
        content = channel_config["content"]
        shorts = content["formats"]["shorts"]
        duration = duration_seconds or int(shorts["duration_seconds"])

        system_prompt = (
            "당신은 얼굴 없는 유튜브 채널의 전문 대본 작가다. "
            "시청 지속률이 높은 대본을 작성하되 확인되지 않은 사실, 과장된 통계, "
            "저작권 있는 문구의 긴 인용을 만들지 않는다. "
            "결과는 제공된 구조를 정확히 따르고, 장면별 내레이션과 시각 자료 프롬프트가 "
            "서로 직접 대응해야 한다."
        )
        user_prompt = f"""
다음 조건으로 유튜브 Shorts 대본을 작성하라.

- 주제: {clean_topic}
- 언어: {channel.get('language', 'ko-KR')}
- 채널 분야: {content.get('niche', '미정')}
- 대상 시청자: {content.get('audience', '일반 시청자')}
- 말투: {content.get('tone', '명확한 설명체')}
- 목표 길이: 약 {duration}초
- 장면 수: 5~8개

성공 기준:
- 첫 2초 안에 호기심을 만드는 훅
- 짧고 자연스럽게 읽히는 내레이션
- 각 장면에 AI 이미지 생성용 visual_prompt 포함
- 마지막에는 짧은 마무리 또는 행동 유도 문장
- 제목은 100자 이하
""".strip()

        return self.provider.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_type=YoutubeScript,
        )

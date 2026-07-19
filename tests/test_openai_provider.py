from types import SimpleNamespace

from ai_youtube.domain.models import YoutubeScript
from ai_youtube.providers.openai_provider import OpenAITextProvider


class FakeResponses:
    def parse(self, **kwargs):
        return SimpleNamespace(
            output_parsed=YoutubeScript(
                topic="테스트",
                title="테스트 제목",
                hook="테스트 훅",
                scenes=[
                    {
                        "scene_number": 1,
                        "narration": "테스트 내레이션",
                        "visual_prompt": "테스트 이미지",
                    }
                ],
                outro="테스트 마무리",
                description="테스트 설명",
                tags=["테스트"],
            )
        )


class FakeClient:
    responses = FakeResponses()


def test_openai_provider_accepts_injected_client() -> None:
    provider = OpenAITextProvider(
        api_key="test", model="test-model", client=FakeClient()
    )
    result = provider.generate_structured("system", "user", YoutubeScript)
    assert result.title == "테스트 제목"

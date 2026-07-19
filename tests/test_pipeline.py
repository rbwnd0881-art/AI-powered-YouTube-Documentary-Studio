from ai_youtube.pipeline.orchestrator import create_job_plan
from ai_youtube.pipeline.stages.script import YoutubeScriptService


class FakeTextProvider:
    def generate_structured(self, system_prompt, user_prompt, output_type):
        return output_type(
            topic="꿈",
            title="꿈을 잊는 이유",
            hook="눈을 뜨자마자 꿈이 사라지는 이유가 있습니다.",
            scenes=[
                {
                    "scene_number": 1,
                    "narration": "뇌는 꿈을 장기 기억으로 잘 저장하지 않습니다.",
                    "visual_prompt": "잠든 사람과 빛나는 뇌, 세로형 일러스트",
                    "on_screen_text": "꿈은 왜 사라질까?",
                }
            ],
            outro="다음 꿈은 일어나자마자 기록해 보세요.",
            description="꿈을 쉽게 잊는 이유를 설명합니다.",
            tags=["꿈", "뇌과학"],
        )


def test_create_job_plan() -> None:
    plan = create_job_plan({"channel": {"id": "test_channel"}}, "test idea")
    assert plan["job"]["channel_id"] == "test_channel"
    assert plan["job"]["idea"] == "test idea"
    assert plan["stages"][0] == "script"


def test_generate_script_with_reusable_provider() -> None:
    channel = {
        "channel": {"id": "test", "language": "ko-KR"},
        "content": {
            "niche": "뇌과학",
            "audience": "일반 시청자",
            "tone": "쉬운 설명체",
            "formats": {"shorts": {"duration_seconds": 45}},
        },
    }
    result = YoutubeScriptService(FakeTextProvider()).generate("꿈", channel)
    assert result.title == "꿈을 잊는 이유"
    assert result.scenes[0].scene_number == 1

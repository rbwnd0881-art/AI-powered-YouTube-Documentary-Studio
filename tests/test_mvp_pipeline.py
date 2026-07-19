import json

from ai_youtube.domain.models import GeneratedSceneAssetsPlan, YoutubeScript
from ai_youtube.pipeline.orchestrator import MvpPipeline
from ai_youtube.providers.placeholder_image_provider import PlaceholderImageProvider


class FakeTextProvider:
    def __init__(self):
        self.calls = 0

    def generate_structured(self, system_prompt, user_prompt, output_type):
        self.calls += 1
        if output_type is YoutubeScript:
            return YoutubeScript(
                topic="꿈",
                title="꿈 테스트",
                hook="꿈은 왜 사라질까요?",
                scenes=[
                    {
                        "scene_number": 1,
                        "narration": "뇌는 모든 꿈을 저장하지 않습니다.",
                        "visual_prompt": "glowing brain",
                        "on_screen_text": "꿈과 기억",
                    }
                ],
                outro="일어나자마자 기록해 보세요.",
                description="꿈과 기억을 설명합니다.",
                tags=["꿈"],
            )
        return GeneratedSceneAssetsPlan(
            scenes=[
                {
                    "source_id": "hook",
                    "image_prompt": "night sky",
                    "video_prompt": "slow zoom",
                    "subtitle": "꿈은 왜 사라질까",
                },
                {
                    "source_id": "body_1",
                    "image_prompt": "glowing brain",
                    "video_prompt": "gentle pulse",
                    "subtitle": "모든 꿈은 저장되지 않는다",
                },
                {
                    "source_id": "outro",
                    "image_prompt": "dream journal",
                    "video_prompt": "camera tilts down",
                    "subtitle": "일어나자마자 기록하세요",
                },
            ]
        )


class FakeSpeechProvider:
    def __init__(self):
        self.calls = 0

    def synthesize(self, text, output_path, **kwargs):
        self.calls += 1
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-mp3")
        return output_path


class FakeEditor:
    def __init__(self):
        self.calls = 0

    def render(self, scene_plan, manifest, output_path):
        self.calls += 1
        output_path.write_bytes(b"fake-mp4")
        return output_path


def channel_config():
    return {
        "channel": {"id": "test", "language": "ko-KR"},
        "content": {
            "niche": "뇌과학",
            "audience": "일반 시청자",
            "tone": "쉬운 설명체",
            "formats": {
                "shorts": {
                    "duration_seconds": 45,
                    "aspect_ratio": "9:16",
                    "resolution": [320, 568],
                }
            },
        },
        "voice": {"voice": "marin", "speed": 1.0},
    }


def app_config():
    return {
        "scene_generation": {
            "visual_style": "cinematic",
            "image_prompt_language": "en",
            "video_prompt_language": "en",
            "subtitle_language": "ko-KR",
            "max_subtitle_characters": 45,
        },
        "speech_generation": {
            "response_format": "mp3",
            "max_input_characters": 4096,
            "voice": "marin",
            "instructions": "natural",
        },
    }


def test_mvp_pipeline_creates_and_reuses_all_artifacts(tmp_path):
    text = FakeTextProvider()
    speech = FakeSpeechProvider()
    editor = FakeEditor()
    pipeline = MvpPipeline(text, speech, PlaceholderImageProvider(), editor)

    result = pipeline.run("꿈", tmp_path, channel_config(), app_config())
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))

    assert result.read_bytes() == b"fake-mp4"
    assert state["status"] == "completed"
    assert state["completed_stages"] == list(MvpPipeline.STAGES)
    assert len(list((tmp_path / "media").glob("*.png"))) == 3
    assert text.calls == 2
    assert speech.calls == 1
    assert editor.calls == 1

    pipeline.run("꿈", tmp_path, channel_config(), app_config())
    assert text.calls == 2
    assert speech.calls == 1
    assert editor.calls == 1


def test_mvp_pipeline_records_failure(tmp_path):
    class BrokenTextProvider(FakeTextProvider):
        def generate_structured(self, *args, **kwargs):
            raise RuntimeError("temporary API failure")

    pipeline = MvpPipeline(
        BrokenTextProvider(), FakeSpeechProvider(), PlaceholderImageProvider(), FakeEditor()
    )

    try:
        pipeline.run("꿈", tmp_path, channel_config(), app_config())
    except RuntimeError:
        pass
    else:
        raise AssertionError("실패가 호출자에게 전달되어야 합니다.")

    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["status"] == "failed"
    assert state["current_stage"] == "script"
    assert "temporary API failure" in state["error"]

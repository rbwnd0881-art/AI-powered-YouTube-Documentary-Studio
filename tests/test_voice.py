import json
from pathlib import Path

import pytest

from ai_youtube.domain.models import YoutubeScript
from ai_youtube.pipeline.stages.voice import YoutubeVoiceService
from ai_youtube.providers.openai_provider import OpenAISpeechProvider


SCRIPT_DATA = {
    "topic": "꿈",
    "title": "꿈을 잊는 이유",
    "hook": "눈을 뜨자마자 꿈이 사라지는 이유가 있습니다.",
    "scenes": [
        {
            "scene_number": 1,
            "narration": "뇌는 꿈을 장기 기억으로 잘 저장하지 않습니다.",
            "visual_prompt": "잠든 사람과 빛나는 뇌",
        }
    ],
    "outro": "다음 꿈은 바로 기록해 보세요.",
    "description": "꿈에 대한 설명",
    "tags": ["꿈"],
}


class FakeStreamingResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def stream_to_file(self, path):
        Path(path).write_bytes(b"fake-mp3")


class FakeSpeechEndpoint:
    def __init__(self):
        self.with_streaming_response = self
        self.last_request = None

    def create(self, **kwargs):
        self.last_request = kwargs
        return FakeStreamingResponse()


class FakeClient:
    def __init__(self):
        self.audio = type("Audio", (), {"speech": FakeSpeechEndpoint()})()


def test_voice_service_loads_script_and_builds_narration(tmp_path):
    script_path = tmp_path / "script.json"
    script_path.write_text(json.dumps(SCRIPT_DATA, ensure_ascii=False), encoding="utf-8")
    script = YoutubeVoiceService.load_script(script_path)
    assert "장기 기억" in script.narration_text()


def test_openai_speech_provider_writes_atomically(tmp_path):
    client = FakeClient()
    provider = OpenAISpeechProvider(
        api_key="test", model="gpt-4o-mini-tts", client=client
    )
    output = provider.synthesize(
        text="테스트",
        output_path=tmp_path / "voice.mp3",
        voice="marin",
        instructions="자연스럽게",
        response_format="mp3",
        speed=1.0,
    )
    assert output.read_bytes() == b"fake-mp3"
    assert client.audio.speech.last_request["voice"] == "marin"


def test_voice_service_rejects_oversized_input(tmp_path):
    script = YoutubeScript.model_validate({**SCRIPT_DATA, "hook": "가" * 50})
    provider = OpenAISpeechProvider(
        api_key="test", model="test", client=FakeClient()
    )
    service = YoutubeVoiceService(provider)
    with pytest.raises(ValueError, match="API 한도"):
        service.generate(
            script=script,
            output_path=tmp_path / "voice.mp3",
            channel_config={"voice": {"voice": "marin", "speed": 1.0}},
            speech_config={
                "max_input_characters": 10,
                "response_format": "mp3",
                "voice": "marin",
                "instructions": "자연스럽게",
            },
        )

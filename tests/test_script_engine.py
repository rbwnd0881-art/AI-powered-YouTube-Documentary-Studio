from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from ai_youtube.script_engine import ScriptEngine, ScriptEngineOutput


VALID_OUTPUT = {
    "hook": "An octopus has not one heart, but three.",
    "narration": (
        "An octopus has not one heart, but three. Two branchial hearts move blood "
        "through the gills, while one systemic heart sends it around the body. "
        "Together, they support the octopus in its oxygen-poor underwater world."
    ),
    "scene_prompts": [
        "octopus with three anatomical heart markers",
        "two branchial hearts beside octopus gills",
        "one systemic heart circulating blood",
        "healthy octopus swimming underwater",
    ],
    "youtube_title": "Why an Octopus Has Three Hearts",
    "youtube_description": "A concise explanation of the octopus circulatory system.",
    "keywords": ["octopus", "three hearts", "marine biology"],
}


class FakeResponses:
    def __init__(self, output):
        self.output = output
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_parsed=self.output)


class FakeClient:
    def __init__(self, output):
        self.responses = FakeResponses(output)


def test_script_engine_returns_valid_schema_and_four_prompts():
    client = FakeClient(ScriptEngineOutput.model_validate(VALID_OUTPUT))
    engine = ScriptEngine(model="test-model", client=client)

    result = engine.generate("Why an octopus has three hearts")

    assert result.model_dump() == VALID_OUTPUT
    assert len(result.scene_prompts) == 4
    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert call["text_format"] is ScriptEngineOutput
    assert "en-US" in call["input"][1]["content"]


def test_script_engine_requires_api_key_without_injected_client(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        ScriptEngine(model="test-model")


def test_script_engine_supports_language_override():
    client = FakeClient(ScriptEngineOutput.model_validate(VALID_OUTPUT))
    engine = ScriptEngine(model="test-model", client=client)

    engine.generate("문어의 심장이 세 개인 이유", language="ko-KR")

    assert "ko-KR" in client.responses.calls[0]["input"][1]["content"]


def test_script_output_parser_is_deterministic():
    first = ScriptEngineOutput.model_validate(VALID_OUTPUT)
    second = ScriptEngineOutput.model_validate(dict(VALID_OUTPUT))

    assert first == second
    assert first.model_dump_json() == second.model_dump_json()


def test_script_output_rejects_wrong_scene_count():
    invalid = {**VALID_OUTPUT, "scene_prompts": VALID_OUTPUT["scene_prompts"][:3]}

    with pytest.raises(ValidationError):
        ScriptEngineOutput.model_validate(invalid)


def test_script_output_requires_hook_at_narration_start():
    invalid = {**VALID_OUTPUT, "narration": "A different first sentence."}

    with pytest.raises(ValidationError, match="hook"):
        ScriptEngineOutput.model_validate(invalid)

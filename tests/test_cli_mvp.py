from pathlib import Path

from typer.testing import CliRunner

import ai_youtube.cli as cli_module


runner = CliRunner()


def test_mvp_video_command_wires_pipeline_without_external_calls(monkeypatch, tmp_path):
    captured = {}

    class FakeSettings:
        openai_api_key = "test-key"
        openai_text_model = None
        openai_tts_model = None
        storage_dir = tmp_path

    class FakeProvider:
        def __init__(self, **kwargs):
            captured.setdefault("providers", []).append(kwargs)

    class FakePipeline:
        def __init__(self, **kwargs):
            captured["pipeline"] = kwargs

        def run(self, topic, job_dir, channel_config, app_config):
            captured["run"] = (topic, job_dir, channel_config, app_config)
            result = Path(job_dir) / "final.mp4"
            result.parent.mkdir(parents=True, exist_ok=True)
            result.write_bytes(b"fake")
            return result

    app_config = {
        "script_generation": {
            "model": "text-model",
            "timeout_seconds": 60,
            "max_retries": 3,
        },
        "speech_generation": {
            "model": "speech-model",
            "timeout_seconds": 120,
            "max_retries": 3,
        },
        "editing": {},
    }
    channel_config = {"channel": {"id": "channel_001"}}
    monkeypatch.setattr(cli_module, "Settings", FakeSettings)
    monkeypatch.setattr(cli_module, "load_app_config", lambda: app_config)
    monkeypatch.setattr(cli_module, "load_channel_config", lambda _: channel_config)
    monkeypatch.setattr(cli_module, "require_openai_api_key", lambda _: "test-key")
    monkeypatch.setattr(cli_module, "OpenAITextProvider", FakeProvider)
    monkeypatch.setattr(cli_module, "OpenAISpeechProvider", FakeProvider)
    monkeypatch.setattr(cli_module, "FFmpegEditor", lambda _: object())
    monkeypatch.setattr(cli_module, "MvpPipeline", FakePipeline)

    job_dir = tmp_path / "job"
    result = runner.invoke(
        cli_module.app,
        ["mvp-video", "--topic", "꿈과 기억", "--job-dir", str(job_dir)],
    )

    assert result.exit_code == 0, result.output
    assert captured["run"][0] == "꿈과 기억"
    assert captured["run"][1] == job_dir
    assert len(captured["providers"]) == 2
    assert (job_dir / "final.mp4").is_file()

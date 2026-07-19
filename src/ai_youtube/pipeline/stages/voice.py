import json
from pathlib import Path
from typing import Any, Optional

from ai_youtube.domain.models import YoutubeScript
from ai_youtube.providers.base import SpeechProvider


SUPPORTED_FORMATS = {"mp3", "opus", "aac", "flac", "wav", "pcm"}


class YoutubeVoiceService:
    def __init__(self, provider: SpeechProvider) -> None:
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

    def generate(
        self,
        script: YoutubeScript,
        output_path: Path,
        channel_config: dict[str, Any],
        speech_config: dict[str, Any],
        voice_override: Optional[str] = None,
    ) -> Path:
        text = script.narration_text()
        max_characters = int(speech_config["max_input_characters"])
        if len(text) > max_characters:
            raise ValueError(
                f"음성 입력이 {len(text)}자로 API 한도 {max_characters}자를 초과했습니다. "
                "Long Form 분할 기능이 필요합니다."
            )

        response_format = str(speech_config["response_format"]).lower()
        if response_format not in SUPPORTED_FORMATS:
            raise ValueError(f"지원하지 않는 음성 형식입니다: {response_format}")
        if output_path.suffix.lower() != f".{response_format}":
            raise ValueError(f"출력 파일 확장자는 .{response_format}이어야 합니다.")

        channel_voice = channel_config.get("voice", {})
        voice = voice_override or channel_voice.get("voice") or speech_config["voice"]
        speed = float(channel_voice.get("speed", 1.0))
        if not 0.25 <= speed <= 4.0:
            raise ValueError("음성 속도는 0.25에서 4.0 사이여야 합니다.")

        return self.provider.synthesize(
            text=text,
            output_path=output_path,
            voice=str(voice),
            instructions=str(speech_config["instructions"]),
            response_format=response_format,
            speed=speed,
        )

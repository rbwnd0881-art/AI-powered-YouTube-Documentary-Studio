"""OpenAI adapters."""

from time import sleep
from typing import Any, Optional, TypeVar
from pathlib import Path

from openai import (
    APIConnectionError,
    APITimeoutError,
    APIStatusError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from pydantic import BaseModel


OutputModel = TypeVar("OutputModel", bound=BaseModel)


class ScriptGenerationError(RuntimeError):
    """Raised when a script cannot be generated safely."""


class SpeechGenerationError(RuntimeError):
    """Raised when speech audio cannot be generated safely."""


class OpenAITextProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 60,
        max_retries: int = 3,
        client: Optional[Any] = None,
    ) -> None:
        self.model = model
        self.max_retries = max(1, max_retries)
        self.client = client or OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=0)

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_type: type[OutputModel],
    ) -> OutputModel:
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.responses.parse(
                    model=self.model,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    text_format=output_type,
                )
                parsed = response.output_parsed
                if parsed is None:
                    raise ScriptGenerationError("OpenAI 응답에 구조화된 대본이 없습니다.")
                return parsed
            except (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError) as exc:
                if attempt >= self.max_retries:
                    raise ScriptGenerationError(
                        f"OpenAI API 일시 오류가 {self.max_retries}회 반복됐습니다: {exc}"
                    ) from exc
                sleep(min(2 ** (attempt - 1), 8))
            except APIStatusError as exc:
                raise ScriptGenerationError(
                    f"OpenAI API 요청이 거절됐습니다 (HTTP {exc.status_code}): {exc.message}"
                ) from exc
            except ScriptGenerationError:
                raise
            except Exception as exc:
                raise ScriptGenerationError(f"대본 생성 중 예상하지 못한 오류가 발생했습니다: {exc}") from exc

        raise ScriptGenerationError("대본을 생성하지 못했습니다.")


class OpenAISpeechProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 120,
        max_retries: int = 3,
        client: Optional[Any] = None,
    ) -> None:
        self.model = model
        self.max_retries = max(1, max_retries)
        self.client = client or OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=0)

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str,
        instructions: str,
        response_format: str = "mp3",
        speed: float = 1.0,
    ) -> Path:
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = output_path.with_name(f".{output_path.name}.part")

        for attempt in range(1, self.max_retries + 1):
            try:
                temporary_path.unlink(missing_ok=True)
                request = dict(
                    model=self.model,
                    voice=voice,
                    input=text,
                    response_format=response_format,
                    speed=speed,
                )
                if self.model not in {"tts-1", "tts-1-hd"}:
                    request["instructions"] = instructions

                with self.client.audio.speech.with_streaming_response.create(
                    **request
                ) as response:
                    response.stream_to_file(temporary_path)

                if not temporary_path.exists() or temporary_path.stat().st_size == 0:
                    raise SpeechGenerationError("OpenAI가 빈 음성 파일을 반환했습니다.")
                temporary_path.replace(output_path)
                return output_path
            except (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError) as exc:
                temporary_path.unlink(missing_ok=True)
                if attempt >= self.max_retries:
                    raise SpeechGenerationError(
                        f"OpenAI 음성 API 일시 오류가 {self.max_retries}회 반복됐습니다: {exc}"
                    ) from exc
                sleep(min(2 ** (attempt - 1), 8))
            except APIStatusError as exc:
                temporary_path.unlink(missing_ok=True)
                raise SpeechGenerationError(
                    f"OpenAI 음성 API 요청이 거절됐습니다 (HTTP {exc.status_code}): {exc.message}"
                ) from exc
            except SpeechGenerationError:
                temporary_path.unlink(missing_ok=True)
                raise
            except Exception as exc:
                temporary_path.unlink(missing_ok=True)
                raise SpeechGenerationError(
                    f"음성 생성 중 예상하지 못한 오류가 발생했습니다: {exc}"
                ) from exc

        raise SpeechGenerationError("음성을 생성하지 못했습니다.")

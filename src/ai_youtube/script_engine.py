"""Minimal structured Shorts script generator using the OpenAI Responses API."""

import logging
import os
from typing import Any, Optional

from openai import OpenAI
from pydantic import BaseModel, Field, model_validator


logger = logging.getLogger(__name__)


class ScriptEngineOutput(BaseModel):
    """Validated output required by the M4 script engine."""

    hook: str = Field(min_length=1)
    narration: str = Field(min_length=1)
    scene_prompts: list[str] = Field(min_length=4, max_length=4)
    youtube_title: str = Field(min_length=1, max_length=100)
    youtube_description: str = Field(min_length=1, max_length=5000)
    keywords: list[str] = Field(min_length=1, max_length=15)

    @model_validator(mode="after")
    def hook_starts_narration(self) -> "ScriptEngineOutput":
        if not self.narration.strip().startswith(self.hook.strip()):
            raise ValueError("narration은 hook 문장으로 시작해야 합니다.")
        return self


class ScriptEngineError(RuntimeError):
    """Raised when the Responses API does not return a valid script."""


class ScriptEngine:
    """Generate one localized, structured Shorts script from a topic."""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        timeout_seconds: float = 60,
        client: Optional[Any] = None,
        default_language: str = "en-US",
    ) -> None:
        self.model = model
        self.default_language = default_language
        if client is not None:
            self.client = client
            return
        resolved_key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        if not resolved_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        self.client = OpenAI(
            api_key=resolved_key,
            timeout=timeout_seconds,
            max_retries=0,
        )

    def generate(
        self,
        topic: str,
        language: Optional[str] = None,
    ) -> ScriptEngineOutput:
        clean_topic = topic.strip()
        if not clean_topic:
            raise ValueError("주제를 한 글자 이상 입력하세요.")
        output_language = (language or self.default_language).strip()
        if not output_language:
            raise ValueError("출력 언어가 필요합니다.")

        system_prompt = (
            "You write concise, factual scripts for faceless YouTube Shorts. "
            "Return the requested structured output only. Do not invent statistics, "
            "quotes, sources, or unverifiable claims. Each visual prompt must directly "
            "correspond to its part of the narration and must not contain written text."
        )
        user_prompt = f"""
Create a YouTube Shorts package for this topic: {clean_topic}

Output language: {output_language}
Spoken narration target: 30 to 45 seconds
Scene count: exactly 4

Requirements:
- The hook must be one complete first sentence.
- The narration must begin verbatim with the hook.
- Write one continuous narration suitable for natural speech.
- Produce exactly four detailed image-generation prompts in narration order.
- Keep the YouTube title at 100 characters or fewer.
- Provide a concise description and relevant search keywords.
- Do not include citations or formatting outside the structured fields.
""".strip()

        logger.info("Shorts 대본 생성을 시작합니다: model=%s", self.model)
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                text_format=ScriptEngineOutput,
            )
        except Exception as exc:
            raise ScriptEngineError("OpenAI Responses API 대본 생성에 실패했습니다.") from exc
        parsed = response.output_parsed
        if parsed is None:
            raise ScriptEngineError("OpenAI 응답에 구조화된 대본이 없습니다.")
        if not isinstance(parsed, ScriptEngineOutput):
            parsed = ScriptEngineOutput.model_validate(parsed)
        logger.info("Shorts 대본 생성이 완료되었습니다.")
        return parsed

"""OpenAI Images API adapter."""

import base64
import binascii
import logging
import os
from io import BytesIO
from pathlib import Path
from time import sleep
from typing import Any, Optional

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from PIL import Image, ImageOps


logger = logging.getLogger(__name__)


class ImageGenerationError(RuntimeError):
    """Raised when an image cannot be generated or saved safely."""


class OpenAIImageProvider:
    """Generate one image and adapt it to the requested output dimensions."""

    def __init__(
        self,
        model: str = "gpt-image-2",
        quality: str = "low",
        api_size: str = "1024x1536",
        max_retries: int = 3,
        timeout_seconds: float = 120,
        api_key: Optional[str] = None,
        client: Optional[Any] = None,
    ) -> None:
        self.model = model
        self.quality = quality
        self.api_size = api_size
        self.max_retries = max(1, max_retries)
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
        prompt: str,
        output_path: Path,
        width: int,
        height: int,
        label: str = "",
    ) -> Path:
        del label
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise ValueError("이미지 프롬프트가 비어 있습니다.")
        if width < 64 or height < 64:
            raise ValueError("이미지 크기는 최소 64x64여야 합니다.")

        logger.info(
            "OpenAI 이미지 생성을 시작합니다: model=%s, size=%s, quality=%s",
            self.model,
            self.api_size,
            self.quality,
        )
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.images.generate(
                    model=self.model,
                    prompt=clean_prompt,
                    size=self.api_size,
                    quality=self.quality,
                    n=1,
                )
                encoded = response.data[0].b64_json if response.data else None
                if not encoded:
                    raise ImageGenerationError(
                        "OpenAI 이미지 응답에 이미지 데이터가 없습니다."
                    )
                saved_path = self._save_image(encoded, output_path, width, height)
                logger.info("OpenAI 이미지를 저장했습니다: %s", saved_path)
                return saved_path
            except APIStatusError as exc:
                if exc.status_code == 429 or exc.status_code >= 500:
                    if attempt < self.max_retries:
                        logger.warning(
                            "OpenAI 이미지 요청을 재시도합니다: status=%s, attempt=%s/%s",
                            exc.status_code,
                            attempt,
                            self.max_retries,
                        )
                        sleep(min(2 ** (attempt - 1), 8))
                        continue
                raise ImageGenerationError(
                    f"OpenAI 이미지 요청 실패 (HTTP {exc.status_code})."
                ) from exc
            except (APIConnectionError, APITimeoutError) as exc:
                raise ImageGenerationError("OpenAI 이미지 API 연결에 실패했습니다.") from exc

        raise ImageGenerationError("OpenAI 이미지를 생성하지 못했습니다.")

    @staticmethod
    def _save_image(
        encoded: str,
        output_path: Path,
        width: int,
        height: int,
    ) -> Path:
        try:
            image_bytes = base64.b64decode(encoded, validate=True)
            with Image.open(BytesIO(image_bytes)) as source:
                image = ImageOps.fit(
                    source.convert("RGB"),
                    (width, height),
                    method=Image.Resampling.LANCZOS,
                )
                output_path = output_path.resolve()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = output_path.with_name(f".{output_path.name}.part")
                image.save(temporary, format="PNG", optimize=True)
                temporary.replace(output_path)
                return output_path
        except (binascii.Error, OSError, ValueError) as exc:
            raise ImageGenerationError(
                "OpenAI 이미지 응답을 유효한 PNG로 저장하지 못했습니다."
            ) from exc

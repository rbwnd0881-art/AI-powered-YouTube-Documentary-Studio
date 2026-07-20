"""Provider construction from application settings."""

from typing import Any, Optional

from ai_youtube.config import Settings, require_openai_api_key
from ai_youtube.providers.base import VisualProvider
from ai_youtube.providers.openai_image_provider import OpenAIImageProvider
from ai_youtube.providers.placeholder_image_provider import PlaceholderImageProvider


def create_visual_provider(
    provider_name: str,
    settings: Settings,
    image_config: dict[str, Any],
    client: Optional[Any] = None,
) -> VisualProvider:
    """Create the configured visual provider without changing the pipeline."""
    normalized = provider_name.strip().lower()
    if normalized == "placeholder":
        return PlaceholderImageProvider()
    if normalized == "openai":
        return OpenAIImageProvider(
            api_key=require_openai_api_key(settings),
            model=settings.openai_image_model or image_config["model"],
            quality=image_config["quality"],
            api_size=image_config["api_size"],
            max_retries=int(image_config["max_retries"]),
            timeout_seconds=float(image_config["timeout_seconds"]),
            client=client,
        )
    raise ValueError(f"지원하지 않는 이미지 Provider입니다: {provider_name}")

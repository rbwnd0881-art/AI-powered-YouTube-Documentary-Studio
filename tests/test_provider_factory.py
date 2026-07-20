from ai_youtube.providers.factory import create_visual_provider
from ai_youtube.providers.openai_image_provider import OpenAIImageProvider
from ai_youtube.providers.placeholder_image_provider import PlaceholderImageProvider


class FakeSettings:
    openai_api_key = "test-key"
    openai_image_model = None


def image_config():
    return {
        "model": "gpt-image-2",
        "quality": "low",
        "api_size": "1024x1536",
        "max_retries": 3,
        "timeout_seconds": 120,
    }


def test_factory_selects_openai_provider():
    provider = create_visual_provider(
        "openai", FakeSettings(), image_config(), client=object()
    )

    assert isinstance(provider, OpenAIImageProvider)


def test_factory_selects_placeholder_provider():
    provider = create_visual_provider("placeholder", FakeSettings(), image_config())

    assert isinstance(provider, PlaceholderImageProvider)

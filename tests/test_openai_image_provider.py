import base64
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import (
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)
from PIL import Image

from ai_youtube.providers.openai_image_provider import (
    ImageGenerationError,
    OpenAIImageProvider,
)


def encoded_png() -> str:
    buffer = BytesIO()
    Image.new("RGB", (64, 96), "navy").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def api_error(error_type, status_code):
    request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
    response = httpx.Response(status_code, request=request)
    return error_type("request failed", response=response, body={})


def test_openai_image_provider_saves_requested_output_shape(tmp_path):
    client = Mock()
    client.images.generate.return_value = SimpleNamespace(
        data=[SimpleNamespace(b64_json=encoded_png())]
    )
    provider = OpenAIImageProvider(client=client)

    result = provider.generate("cinematic octopus", tmp_path / "scene.png", 320, 568)

    assert result == (tmp_path / "scene.png").resolve()
    with Image.open(result) as image:
        assert image.size == (320, 568)
        assert image.mode == "RGB"
    client.images.generate.assert_called_once_with(
        model="gpt-image-2",
        prompt="cinematic octopus",
        size="1024x1536",
        quality="low",
        n=1,
    )


@pytest.mark.parametrize(
    ("error_type", "status_code"),
    [(RateLimitError, 429), (InternalServerError, 500)],
)
def test_openai_image_provider_retries_only_retryable_statuses(
    monkeypatch, tmp_path, error_type, status_code
):
    monkeypatch.setattr("ai_youtube.providers.openai_image_provider.sleep", lambda _: None)
    client = Mock()
    client.images.generate.side_effect = [
        api_error(error_type, status_code),
        SimpleNamespace(data=[SimpleNamespace(b64_json=encoded_png())]),
    ]
    provider = OpenAIImageProvider(client=client, max_retries=2)

    provider.generate("octopus", tmp_path / "retry.png", 320, 568)

    assert client.images.generate.call_count == 2


@pytest.mark.parametrize(
    ("error_type", "status_code"),
    [(AuthenticationError, 401), (BadRequestError, 400)],
)
def test_openai_image_provider_does_not_retry_client_errors(
    tmp_path, error_type, status_code
):
    client = Mock()
    client.images.generate.side_effect = api_error(error_type, status_code)
    provider = OpenAIImageProvider(client=client, max_retries=3)

    with pytest.raises(ImageGenerationError, match=f"HTTP {status_code}"):
        provider.generate("octopus", tmp_path / "client-error.png", 320, 568)

    assert client.images.generate.call_count == 1


def test_openai_image_provider_rejects_invalid_response(tmp_path):
    client = Mock()
    client.images.generate.return_value = SimpleNamespace(
        data=[SimpleNamespace(b64_json="not-base64")]
    )
    provider = OpenAIImageProvider(client=client)

    with pytest.raises(ImageGenerationError, match="유효한 PNG"):
        provider.generate("octopus", tmp_path / "invalid.png", 320, 568)

from PIL import Image

from ai_youtube.providers.placeholder_image_provider import PlaceholderImageProvider


def test_placeholder_image_is_repeatable(tmp_path):
    provider = PlaceholderImageProvider()
    first = provider.generate("cinematic brain", tmp_path / "first.png", 320, 568, "장면 1")
    second = provider.generate("cinematic brain", tmp_path / "second.png", 320, 568, "장면 1")

    assert first.read_bytes() == second.read_bytes()
    with Image.open(first) as image:
        assert image.size == (320, 568)
        assert image.mode == "RGB"


def test_placeholder_image_rejects_empty_prompt(tmp_path):
    provider = PlaceholderImageProvider()

    try:
        provider.generate("  ", tmp_path / "empty.png", 320, 568)
    except ValueError as exc:
        assert "비어" in str(exc)
    else:
        raise AssertionError("빈 프롬프트가 거부되어야 합니다.")

from PIL import Image, ImageFont

from ai_youtube.domain.models import PublishingMetadata, YoutubeScript
from ai_youtube.pipeline.stages.publish import ThumbnailRenderer, YoutubePublishingService


SCRIPT = YoutubeScript.model_validate(
    {
        "topic": "꿈",
        "title": "꿈을 잊는 이유",
        "hook": "꿈이 사라지는 이유가 있습니다.",
        "scenes": [
            {
                "scene_number": 1,
                "narration": "뇌는 꿈을 장기 기억으로 잘 저장하지 않습니다.",
                "visual_prompt": "glowing brain",
            }
        ],
        "outro": "꿈을 바로 기록해 보세요.",
        "description": "꿈 설명",
        "tags": ["꿈"],
    }
)


class FakeMetadataProvider:
    def generate_structured(self, system_prompt, user_prompt, output_type):
        assert output_type is PublishingMetadata
        return output_type(
            title="꿈을 금방 잊는 진짜 이유",
            description="꿈이 기억에서 사라지는 원리를 알아봅니다. #꿈 #뇌과학",
            tags=["꿈", "뇌과학", "수면"],
            thumbnail_text="꿈은 왜 사라질까",
        )


def test_metadata_adds_disclosure_and_deduplicates_tags():
    service = YoutubePublishingService(FakeMetadataProvider())
    result = service.generate_metadata(
        SCRIPT,
        {
            "channel": {"language": "ko-KR"},
            "content": {"niche": "뇌과학", "audience": "일반 시청자"},
            "publishing": {"default_tags": ["꿈", "상식"]},
        },
        {
            "ai_disclosure": "AI로 생성되었습니다.",
            "thumbnail": {"max_text_characters": 28},
        },
    )
    assert result.description.endswith("AI로 생성되었습니다.")
    assert result.tags == ["꿈", "뇌과학", "수면", "상식"]


def test_thumbnail_renderer_creates_small_jpeg(tmp_path, monkeypatch):
    background = tmp_path / "background.png"
    Image.new("RGB", (600, 900), "#446688").save(background)
    monkeypatch.setattr(
        ThumbnailRenderer,
        "_load_font",
        staticmethod(lambda font_path, size: ImageFont.load_default()),
    )
    output = ThumbnailRenderer(
        {
            "width": 1280,
            "height": 720,
            "max_file_bytes": 2_000_000,
            "jpeg_quality": 90,
        }
    ).render(
        background_path=background,
        text="Why Dreams Fade",
        output_path=tmp_path / "thumbnail.jpg",
        brand_config={"primary_color": "#FFFFFF", "font": "missing.ttf"},
    )
    assert output.is_file()
    assert output.stat().st_size < 2_000_000
    assert Image.open(output).size == (1280, 720)

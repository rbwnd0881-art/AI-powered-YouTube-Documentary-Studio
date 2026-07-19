import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

from ai_youtube.domain.models import PublishingMetadata, YoutubeScript
from ai_youtube.providers.base import TextProvider


class YoutubePublishingService:
    def __init__(self, provider: TextProvider) -> None:
        self.provider = provider

    @staticmethod
    def load_script(path: Path) -> YoutubeScript:
        if not path.is_file():
            raise FileNotFoundError(f"대본 파일을 찾을 수 없습니다: {path}")
        try:
            return YoutubeScript.model_validate(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"대본 JSON을 읽을 수 없습니다: {exc}") from exc

    @staticmethod
    def load_metadata(path: Path) -> PublishingMetadata:
        if not path.is_file():
            raise FileNotFoundError(f"메타데이터 파일을 찾을 수 없습니다: {path}")
        try:
            return PublishingMetadata.model_validate(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"메타데이터 JSON을 읽을 수 없습니다: {exc}") from exc

    def generate_metadata(
        self,
        script: YoutubeScript,
        channel_config: dict[str, Any],
        publish_config: dict[str, Any],
    ) -> PublishingMetadata:
        content = channel_config["content"]
        publishing = channel_config["publishing"]
        disclosure = str(publish_config["ai_disclosure"])
        system_prompt = (
            "당신은 YouTube Shorts 메타데이터 편집자다. 낚시성 허위 표현, 과장된 통계, "
            "관련 없는 태그를 만들지 않는다. 제목과 설명은 실제 대본 내용만 반영한다."
        )
        user_prompt = f"""
다음 대본으로 YouTube 게시 메타데이터를 작성하라.

언어: {channel_config['channel'].get('language', 'ko-KR')}
채널 분야: {content.get('niche', '미정')}
대상: {content.get('audience', '일반 시청자')}
기본 태그: {json.dumps(publishing.get('default_tags', []), ensure_ascii=False)}

규칙:
- title은 60자 안팎, 최대 100자
- description은 핵심 요약 2~4문장과 관련 해시태그 최대 3개
- tags는 실제 내용과 직접 관련된 검색어 5~12개, # 기호 제외
- thumbnail_text는 28자 이하의 짧고 명확한 한국어 문구
- AI 생성 고지 문구는 description에 넣지 말 것. 시스템이 별도로 추가한다.

대본 JSON:
{json.dumps(script.model_dump(mode='json'), ensure_ascii=False, indent=2)}
""".strip()
        metadata = self.provider.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_type=PublishingMetadata,
        )
        unique_tags = []
        for tag in [*metadata.tags, *publishing.get("default_tags", [])]:
            clean = str(tag).strip().lstrip("#")
            if clean and clean not in unique_tags:
                unique_tags.append(clean)
        if len(",".join(unique_tags)) > 450:
            raise ValueError("생성된 태그의 총 길이가 너무 깁니다.")
        if len(metadata.thumbnail_text) > int(
            publish_config["thumbnail"]["max_text_characters"]
        ):
            raise ValueError("썸네일 문구가 설정된 최대 길이를 초과했습니다.")

        description = metadata.description.strip()
        if disclosure not in description:
            description = f"{description}\n\n{disclosure}"
        if len(description) > 5000:
            raise ValueError("AI 고지 문구를 포함한 설명이 5000자를 초과했습니다.")
        return metadata.model_copy(
            update={"description": description, "tags": unique_tags}
        )


class ThumbnailRenderer:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    @staticmethod
    def _load_font(font_path: Path, size: int) -> ImageFont.FreeTypeFont:
        candidates = [
            font_path,
            Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
            Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        ]
        for candidate in candidates:
            if candidate.is_file():
                return ImageFont.truetype(str(candidate), size=size, index=0)
        raise FileNotFoundError(
            "한국어 썸네일 폰트를 찾을 수 없습니다. assets/fonts에 폰트를 추가하세요."
        )

    @staticmethod
    def _wrap_text(text: str, max_chars: int = 12) -> str:
        words = text.split()
        if len(words) <= 1:
            midpoint = max(1, len(text) // 2)
            return text if len(text) <= max_chars else f"{text[:midpoint]}\n{text[midpoint:]}"
        lines, current = [], ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and len(candidate) > max_chars:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return "\n".join(lines[:3])

    def render(
        self,
        background_path: Path,
        text: str,
        output_path: Path,
        brand_config: dict[str, Any],
    ) -> Path:
        if not background_path.is_file():
            raise FileNotFoundError(f"썸네일 배경 이미지가 없습니다: {background_path}")
        if output_path.suffix.lower() not in {".jpg", ".jpeg"}:
            raise ValueError("썸네일 출력 형식은 .jpg 또는 .jpeg여야 합니다.")

        width, height = int(self.config["width"]), int(self.config["height"])
        image = Image.open(background_path).convert("RGB")
        image = ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS)
        image = ImageEnhance.Contrast(image).enhance(1.1)

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle((0, 0, width, height), fill=(0, 0, 0, 80))
        overlay_draw.rectangle((0, height * 0.50, width, height), fill=(0, 0, 0, 145))
        image = Image.alpha_composite(image.convert("RGBA"), overlay)
        draw = ImageDraw.Draw(image)

        configured_font = Path(str(brand_config.get("font", "")))
        font = self._load_font(configured_font, size=96)
        wrapped = self._wrap_text(text)
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=10, stroke_width=4)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = max(60, (width - text_width) // 2)
        y = height - text_height - 80
        draw.multiline_text(
            (x, y),
            wrapped,
            font=font,
            fill=str(brand_config.get("primary_color", "#FFFFFF")),
            stroke_width=5,
            stroke_fill="#000000",
            spacing=10,
            align="center",
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        quality = int(self.config["jpeg_quality"])
        max_bytes = int(self.config["max_file_bytes"])
        while quality >= 55:
            image.convert("RGB").save(
                output_path, format="JPEG", quality=quality, optimize=True
            )
            if output_path.stat().st_size <= max_bytes:
                return output_path.resolve()
            quality -= 5
        output_path.unlink(missing_ok=True)
        raise ValueError("썸네일을 YouTube의 파일 크기 제한 안으로 압축하지 못했습니다.")

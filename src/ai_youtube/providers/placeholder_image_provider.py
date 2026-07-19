"""Free deterministic scene images for MVP pipeline validation."""

import hashlib
import random
from pathlib import Path
from typing import Union

from PIL import Image, ImageDraw, ImageFont


class PlaceholderImageProvider:
    """Create repeatable local images without calling an external API."""

    @staticmethod
    def _font(size: int) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
        candidates = (
            Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        )
        for path in candidates:
            if path.is_file():
                return ImageFont.truetype(str(path), size=size)
        return ImageFont.load_default()

    def generate(
        self,
        prompt: str,
        output_path: Path,
        width: int,
        height: int,
        label: str = "",
    ) -> Path:
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise ValueError("이미지 프롬프트가 비어 있습니다.")
        if width < 64 or height < 64:
            raise ValueError("이미지 크기는 최소 64x64여야 합니다.")

        seed = int(hashlib.sha256(clean_prompt.encode("utf-8")).hexdigest()[:16], 16)
        rng = random.Random(seed)
        base = tuple(rng.randint(20, 110) for _ in range(3))
        accent = tuple(rng.randint(130, 245) for _ in range(3))
        image = Image.new("RGB", (width, height), base)
        draw = ImageDraw.Draw(image, "RGBA")

        for _ in range(18):
            radius = rng.randint(max(30, width // 18), max(60, width // 4))
            x = rng.randint(-radius, width + radius)
            y = rng.randint(-radius, height + radius)
            color = (*accent, rng.randint(18, 65))
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

        overlay_height = max(130, height // 9)
        draw.rectangle((0, height - overlay_height, width, height), fill=(0, 0, 0, 130))
        display_label = label.strip() or "MVP PLACEHOLDER"
        font = self._font(max(30, width // 24))
        bbox = draw.textbbox((0, 0), display_label, font=font)
        x = (width - (bbox[2] - bbox[0])) // 2
        y = height - overlay_height + (overlay_height - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), display_label, font=font, fill=(255, 255, 255, 235))

        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format="PNG", optimize=True)
        return output_path

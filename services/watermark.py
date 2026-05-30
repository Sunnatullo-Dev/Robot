"""Image watermark service.

Anketa rasmiga ko'rinarli ID yozish — screenshot tarqalsa, kim olganini
aniqlash uchun. Bu screenshot'ni bloklamaydi (Telegram bot API'da
bunday imkoniyat yo'q), lekin ekran rasmlari tarqalganda javobgarni
identifikatsiya qilishga yordam beradi.
"""
from __future__ import annotations

import io
import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import BufferedInputFile
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# JPEG sifati (75-95 oraliq, 85 — yaxshi balans)
_JPEG_QUALITY = 85
# Maximum rasm o'lchami (RAM tejash uchun)
_MAX_DIMENSION = 1600


def _get_font(size: int) -> ImageFont.ImageFont:
    """Tizimda mavjud TTF shriftini topish, bo'lmasa default."""
    candidates = [
        "arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _add_watermark(image_bytes: bytes, viewer_id: int) -> bytes:
    """Rasmga viewer ID watermark qo'shish va bytes qaytarish."""
    img = Image.open(io.BytesIO(image_bytes))

    # RGB ga aylantirish (JPEG saqlash uchun)
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Juda katta rasmlarni qisqartirish
    if max(img.size) > _MAX_DIMENSION:
        img.thumbnail((_MAX_DIMENSION, _MAX_DIMENSION), Image.Resampling.LANCZOS)

    width, height = img.size
    draw = ImageDraw.Draw(img, "RGBA")

    # Shrift o'lchami rasmga proporsional
    font_size = max(int(min(width, height) * 0.035), 18)
    font = _get_font(font_size)

    text = f"ID: {viewer_id}"

    # Matn o'lchovi
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Pozitsiya — pastki o'ng burchak, kichik padding bilan
    padding = max(int(font_size * 0.5), 8)
    x = width - text_w - padding * 2
    y = height - text_h - padding * 2

    # Yarim-shaffof qora fon (matn yaxshi ko'rinishi uchun)
    bg_padding = max(int(font_size * 0.3), 4)
    draw.rectangle(
        [
            (x - bg_padding, y - bg_padding),
            (x + text_w + bg_padding, y + text_h + bg_padding),
        ],
        fill=(0, 0, 0, 160),  # 160 / 255 ≈ 63% opacity
    )

    # Oq matn (RGBA bilan, lekin opaqe)
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    # JPEG bytes qaytarish
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
    output.seek(0)
    return output.read()


async def get_watermarked_photo(
    bot: Bot, file_id: str, viewer_id: int,
) -> Optional[BufferedInputFile]:
    """Telegram'dan rasmni yuklab, watermark qo'shib, BufferedInputFile qaytaradi.

    Args:
        bot: aiogram Bot instance
        file_id: Asl rasm file_id
        viewer_id: Kim ko'rayotgan — uning Telegram ID'si

    Returns:
        BufferedInputFile yoki None (xato bo'lsa)
    """
    try:
        # 1) Telegram'dan asl rasmni yuklab olish
        file = await bot.get_file(file_id)
        if not file.file_path:
            return None
        buf = await bot.download_file(file.file_path)
        if buf is None:
            return None
        original_bytes = buf.read()

        # 2) Watermark qo'shish
        watermarked = _add_watermark(original_bytes, viewer_id)

        # 3) BufferedInputFile sifatida qaytarish
        return BufferedInputFile(
            watermarked,
            filename=f"profile_{viewer_id}.jpg",
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Watermark failed for viewer=%s file_id=%s: %s", viewer_id, file_id, e)
        return None

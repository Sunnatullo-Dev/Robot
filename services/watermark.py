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


def _add_deterrent_watermark(image_bytes: bytes) -> bytes:
    """Rasmga 'Tarqatish taqiqlanadi' deterrent watermark qo'shish.

    Shaxsiy ma'lumot YO'Q — faqat ogohlantirish stamp'i.
    Screenshot oluvchi har joydan ko'radi → tarqatishdan to'xtaydi.
    """
    img = Image.open(io.BytesIO(image_bytes))

    if img.mode != "RGB":
        img = img.convert("RGB")

    if max(img.size) > _MAX_DIMENSION:
        img.thumbnail((_MAX_DIMENSION, _MAX_DIMENSION), Image.Resampling.LANCZOS)

    width, height = img.size
    draw = ImageDraw.Draw(img, "RGBA")

    # Asosiy watermark — pastki markazda
    main_size = max(int(min(width, height) * 0.04), 20)
    main_font = _get_font(main_size)
    main_text = "TANISHUV BOT  -  ANONIM"

    bbox = draw.textbbox((0, 0), main_text, font=main_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    padding = max(int(main_size * 0.5), 10)
    x = (width - text_w) // 2
    y = height - text_h - padding * 2

    # Yarim-shaffof fon
    bg_padding = max(int(main_size * 0.4), 6)
    draw.rectangle(
        [
            (x - bg_padding, y - bg_padding),
            (x + text_w + bg_padding, y + text_h + bg_padding),
        ],
        fill=(0, 0, 0, 140),
    )
    draw.text((x, y), main_text, fill=(255, 255, 255, 255), font=main_font)

    # Diagonal "TARQATISH TAQIQLANADI" yozuvi (kuchli deterrent)
    diag_size = max(int(min(width, height) * 0.06), 24)
    diag_font = _get_font(diag_size)
    diag_text = "TARQATISH TAQIQLANADI"

    # Yangi transparent layer va aylantirish
    diag_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    diag_draw = ImageDraw.Draw(diag_layer)
    diag_bbox = diag_draw.textbbox((0, 0), diag_text, font=diag_font)
    diag_w = diag_bbox[2] - diag_bbox[0]
    diag_h = diag_bbox[3] - diag_bbox[1]
    diag_draw.text(
        ((width - diag_w) // 2, (height - diag_h) // 2),
        diag_text,
        fill=(255, 255, 255, 60),  # juda shaffof (kuchsiz ko'rinadi)
        font=diag_font,
    )
    diag_layer = diag_layer.rotate(-25, resample=Image.Resampling.BICUBIC)
    img.paste(diag_layer, (0, 0), diag_layer)

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
    output.seek(0)
    return output.read()


async def get_watermarked_photo(
    bot: Bot, file_id: str, viewer_id: int = 0,
) -> Optional[BufferedInputFile]:
    """Telegram'dan rasmni yuklab, deterrent watermark qo'shib qaytaradi.

    Args:
        bot: aiogram Bot instance
        file_id: Asl rasm file_id
        viewer_id: parametr saqlangan (eski kod uchun), HOZIR ishlatilmaydi —
                   anti-share watermark shaxsiy ma'lumot ko'rsatmaydi.

    Returns:
        BufferedInputFile yoki None (xato bo'lsa)
    """
    try:
        file = await bot.get_file(file_id)
        if not file.file_path:
            return None
        buf = await bot.download_file(file.file_path)
        if buf is None:
            return None
        original_bytes = buf.read()

        # Deterrent watermark — ID yo'q, faqat ogohlantirish
        watermarked = _add_deterrent_watermark(original_bytes)

        return BufferedInputFile(
            watermarked,
            filename="profile.jpg",
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Watermark failed for file_id=%s: %s", file_id, e)
        return None

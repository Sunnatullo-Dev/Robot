"""Terminal'dan ishga tushiriladigan script — 15 ta test anketani DB ga
qo'shadi. Rasmlar pravatar.cc dan olinadi (random avatarlar) va Telegram'ga
yuklab, file_id'lari ishlatiladi.

Foydalanish:
    python -m tools.seed

Bot ishlab turgan bo'lsa ham ishlaydi. Test anketalarni o'chirish:
    python -m tools.seed --delete
"""
from __future__ import annotations

import asyncio
import io
import sys

# Windows terminal'ida emoji va Unicode chiqarish uchun
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import URLInputFile

from config import load_config
from data.test_users import BASE_ID, TEST_USERS
from database import models
from database.db import init_db


# pravatar.cc'dan har xil avatar — birinchi 8 ta ayol, qolgani erkak ko'rinishida
# (img IDs taxminan to'g'ri kelganiga ishonib)
def photo_url_for(index: int, gender: str) -> str:
    """Har bir anketa uchun unique URL."""
    # img=1..70 — pravatar'da mavjud
    # Erkak/ayol uchun farqlay olmaymiz, lekin ID bilan har biri farq qiladi
    return f"https://i.pravatar.cc/400?img={(index % 70) + 1}"


async def seed_all(bot: Bot, admin_chat_id: int) -> int:
    """Test anketalarni yaratadi, har biri uchun rasmni Telegram'ga
    yuklab, file_id'sini ishlatadi.
    """
    created = 0
    failed: list[str] = []

    for i, (gender, name, age, lf, city, bio, lat, lng) in enumerate(TEST_USERS):
        user_id = BASE_ID + i + 1
        try:
            # 1) Rasmni Telegram'ga yuklash (admin chatga, keyin o'chiramiz)
            photo_url = photo_url_for(i, gender)
            sent = await bot.send_photo(
                admin_chat_id,
                photo=URLInputFile(photo_url),
            )
            photo_id = sent.photo[-1].file_id

            # 2) DB ga yozish
            await models.upsert_seed_user(
                user_id=user_id,
                name=name,
                age=age,
                gender=gender,
                looking_for=lf,
                city=city,
                bio=bio,
                photo_id=photo_id,
                latitude=lat,
                longitude=lng,
            )
            created += 1
            print(f"  ✓ #{i+1:2d} {name:10s} ({gender}, {age}, {city.split(',')[0]})")

            # 3) Admin chatdagi rasmni o'chirish (spam bo'lmasligi uchun)
            try:
                await bot.delete_message(admin_chat_id, sent.message_id)
            except TelegramBadRequest:
                pass

        except Exception as e:
            failed.append(f"{name}: {e}")
            print(f"  ✗ #{i+1:2d} {name}: {e}")

    if failed:
        print(f"\n❗️ {len(failed)} ta xatolik")
    return created


async def delete_all() -> int:
    return await models.delete_seed_users(BASE_ID)


async def main() -> int:
    config = load_config()
    await init_db(config.db_path)

    if not config.admin_ids:
        print("❗️ .env faylida ADMIN_IDS ko'rsatilmagan")
        return 1
    admin_chat = config.admin_ids[0]

    # --delete bayrog'i bo'lsa, o'chirish rejimi
    if "--delete" in sys.argv:
        n = await delete_all()
        print(f"🗑 {n} ta test anketa o'chirildi")
        return 0

    bot = Bot(token=config.bot_token)
    try:
        print(f"📥 {len(TEST_USERS)} ta test anketa yaratilmoqda...")
        print(f"   Rasmlar admin chat ({admin_chat}) orqali yuklanadi va o'chiriladi.\n")
        created = await seed_all(bot, admin_chat)
        print(f"\n✅ {created} ta anketa muvaffaqiyatli qo'shildi")
        print("\nBotda /search yoki '🔍 Anketalarni ko'rish' orqali ko'rib chiqing.")
        print("O'chirish uchun: python -m tools.seed --delete")
    finally:
        await bot.session.close()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

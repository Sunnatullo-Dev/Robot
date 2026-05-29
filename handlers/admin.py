import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Config
from data.test_users import BASE_ID, TEST_USERS
from database import models
from keyboards import inline, reply
from states.user_states import AdminFlow

router = Router(name="admin")
logger = logging.getLogger(__name__)


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


@router.message(Command("admin"))
async def admin_panel(message: Message, config: Config) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    await message.answer(
        "<b>🛠 Admin panel</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=inline.admin_menu_kb(),
    )


@router.callback_query(F.data == "adm:stats")
async def admin_stats(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    s = await models.stats()
    text = (
        "<b>📊 Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{s['total_users']}</b>\n"
        f"🟢 Faollar: <b>{s['active_users']}</b>\n"
        f"📝 Anketali: <b>{s['with_profile']}</b>\n"
        f"🚫 Bloklangan: <b>{s['banned_users']}</b>\n\n"
        f"❤️ Like'lar: <b>{s['total_likes']}</b>\n"
        f"💞 Mosliklar: <b>{s['total_matches']}</b>\n"
        f"⚠️ Shikoyatlar: <b>{s['total_reports']}</b>"
    )
    await call.answer()
    await call.message.answer(text)  # type: ignore[union-attr]


@router.callback_query(F.data == "adm:broadcast")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AdminFlow.broadcast)
    await call.answer()
    await call.message.answer(  # type: ignore[union-attr]
        "📢 Yuboriladigan xabar matnini kiriting (yoki ❌ Bekor qilish):",
        reply_markup=reply.cancel_kb(),
    )


@router.message(AdminFlow.broadcast, F.text)
async def admin_broadcast_send(
    message: Message, state: FSMContext, bot: Bot, config: Config,
) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=reply.main_menu())
        return

    text = message.text or ""
    await state.clear()
    ids = await models.all_active_user_ids()
    sent, failed = 0, 0
    status = await message.answer(f"📤 Yuborilmoqda... 0/{len(ids)}")

    for i, uid in enumerate(ids, 1):
        try:
            await bot.send_message(uid, text)
            sent += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(uid, text)
                sent += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        except Exception as e:
            logger.exception("Broadcast error to %s: %s", uid, e)
            failed += 1

        if i % 25 == 0:
            try:
                await status.edit_text(f"📤 Yuborilmoqda... {i}/{len(ids)}")
            except TelegramBadRequest:
                pass
        await asyncio.sleep(0.04)  # ~25 msg/sec — Telegram limiti ostida

    await status.edit_text(
        f"✅ Tarqatish tugadi.\n\nYetkazildi: <b>{sent}</b>\nXato: <b>{failed}</b>"
    )


@router.callback_query(F.data == "adm:ban")
async def admin_ban_start(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AdminFlow.ban_user)
    await call.answer()
    await call.message.answer("Ban qilinadigan foydalanuvchi ID sini yuboring:", reply_markup=reply.cancel_kb())  # type: ignore[union-attr]


@router.callback_query(F.data == "adm:unban")
async def admin_unban_start(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AdminFlow.unban_user)
    await call.answer()
    await call.message.answer("Unban qilinadigan foydalanuvchi ID sini yuboring:", reply_markup=reply.cancel_kb())  # type: ignore[union-attr]


@router.message(AdminFlow.ban_user, F.text)
async def admin_ban_do(message: Message, state: FSMContext, config: Config) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=reply.main_menu())
        return
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("❗️ Faqat raqam (Telegram ID) yuboring.")
        return
    await models.set_banned(int(text), True)
    await state.clear()
    await message.answer(f"🚫 <code>{text}</code> bloklandi.", reply_markup=reply.main_menu())


@router.message(AdminFlow.unban_user, F.text)
async def admin_unban_do(message: Message, state: FSMContext, config: Config) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=reply.main_menu())
        return
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("❗️ Faqat raqam (Telegram ID) yuboring.")
        return
    await models.set_banned(int(text), False)
    await state.clear()
    await message.answer(f"✅ <code>{text}</code> blokdan chiqarildi.", reply_markup=reply.main_menu())


@router.message(Command("stats"))
async def cmd_stats(message: Message, config: Config) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    s = await models.stats()
    await message.answer(
        f"👥 {s['total_users']} • 🟢 {s['active_users']} • "
        f"💞 {s['total_matches']} • ⚠️ {s['total_reports']}"
    )


# ============ TEST ANKETALAR (/seed, /unseed) ============

@router.message(Command("seed"))
async def cmd_seed_start(
    message: Message, state: FSMContext, config: Config,
) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    await state.set_state(AdminFlow.seed_photo)
    await message.answer(
        f"📸 <b>Test anketalar yaratish</b>\n\n"
        f"Hozir <b>bitta rasm</b> yuboring — u {len(TEST_USERS)} ta test "
        f"anketada ishlatiladi (har xil ism/yosh/shahar bilan).\n\n"
        f"Bekor qilish uchun: /cancel",
        reply_markup=reply.cancel_kb(),
    )


@router.message(Command("cancel"), AdminFlow.seed_photo)
async def cmd_seed_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=reply.main_menu())


@router.message(AdminFlow.seed_photo, F.text == "❌ Bekor qilish")
async def seed_cancel_btn(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=reply.main_menu())


@router.message(AdminFlow.seed_photo, F.photo)
async def seed_with_photo(
    message: Message, state: FSMContext, config: Config,
) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    if not message.photo:
        return

    photo_id = message.photo[-1].file_id
    created = 0
    failed: list[str] = []

    for i, (gender, name, age, lf, city, bio, lat, lng) in enumerate(TEST_USERS):
        user_id = BASE_ID + i + 1
        try:
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
        except Exception as e:
            logger.exception("Seed user %s failed: %s", name, e)
            failed.append(f"{name}: {e}")

    await state.clear()
    text = f"✅ <b>{created} ta test anketa yaratildi</b>\n\n"
    if failed:
        text += f"❗️ Muvaffaqiyatsiz: {len(failed)}\n" + "\n".join(failed[:5])
    text += "\n\nO'chirib tashlash uchun: /unseed"
    await message.answer(text, reply_markup=reply.main_menu())


@router.message(AdminFlow.seed_photo)
async def seed_no_photo(message: Message) -> None:
    await message.answer("❗️ Iltimos, rasm yuboring (matn yoki fayl emas).")


@router.message(Command("unseed"))
async def cmd_unseed(message: Message, config: Config) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    deleted = await models.delete_seed_users(BASE_ID)
    await message.answer(
        f"🗑 {deleted} ta test anketa o'chirildi.",
        reply_markup=reply.main_menu(),
    )

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Config
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

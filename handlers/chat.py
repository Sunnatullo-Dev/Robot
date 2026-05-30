"""Anonim suhbat handler — chat moderation system bilan.

Asosiy o'zgarishlar:
1. Match'dan keyin chat boshlanishidan oldin Safety Screen majburiy
2. Har bir xabar content_filter orqali tekshiriladi
3. Buzilish → warn/mute/ban (eskalatsiya)
4. Oddiy chatlar DB ga yozilmaydi (in-memory chat_buffer)
5. Report bo'lganda partner'ning oxirgi 100 xabari DB ga ko'chiriladi
"""
from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from database import models
from database.logs import EventType
from keyboards import inline, reply
from services import chat_buffer
from services.content_filter import detect_violation
from services.logging_service import log_event
from services.moderation_service import format_action_message, handle_violation
from states.user_states import ReportFlow
from utils.helpers import esc

router = Router(name="chat")
logger = logging.getLogger(__name__)


SAFETY_TEXT = (
    "🔒 <b>Xavfsizlik qoidalari</b>\n\n"
    "Anonim suhbat boshlashdan oldin quyidagi qoidalar bilan tanishing:\n\n"
    "• ❌ Telegram username (@username) yuborish <b>taqiqlanadi</b>\n"
    "• ❌ Telefon raqami yuborish <b>taqiqlanadi</b>\n"
    "• ❌ Tashqi havolalar (t.me, instagram, va h.k.) <b>taqiqlanadi</b>\n"
    "• ❌ Spam, haqorat va noqonuniy kontent <b>taqiqlanadi</b>\n\n"
    "<b>Qoidalarni buzganlarga:</b>\n"
    "1-buzilish → ⚠️ Ogohlantirish\n"
    "2-buzilish → 🔇 24 soat mute\n"
    "3-buzilish → 🚫 Doimiy ban\n\n"
    "Davom etish orqali siz qoidalarga rozilik bildirasiz."
)


def _safety_kb(partner_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Roziman", callback_data=f"safety:agree:{partner_id}")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="safety:cancel")],
        ]
    )


# ============ 💬 SUHBAT BOSHLASH ============

@router.callback_query(F.data.startswith("chat_start:"))
async def chat_start(call: CallbackQuery, bot: Bot) -> None:
    """Match'dan keyin chat boshlash. Safety screen majburiy."""
    if call.data is None or call.from_user is None or call.message is None:
        return
    partner_id = int(call.data.split(":", 1)[1])

    # Match mavjudligini tekshirish
    matches = await models.get_matches(call.from_user.id)
    match_id = next((m["match_id"] for m in matches if m["user_id"] == partner_id), None)
    if match_id is None:
        await call.answer("Bu odam bilan moslik yo'q.", show_alert=True)
        return

    # Safety screen — agar foydalanuvchi hali rozi bo'lmagan bo'lsa
    if not await models.has_agreed_safety(call.from_user.id):
        await call.answer()
        await call.message.answer(  # type: ignore[union-attr]
            SAFETY_TEXT, reply_markup=_safety_kb(partner_id),
        )
        return

    # Rozilik allaqachon — to'g'ridan-to'g'ri boshlaymiz
    await _do_start_chat(call, bot, partner_id, match_id)


@router.callback_query(F.data.startswith("safety:agree:"))
async def safety_agreed(call: CallbackQuery, bot: Bot) -> None:
    if call.data is None or call.from_user is None or call.message is None:
        return
    partner_id = int(call.data.split(":")[-1])
    await models.mark_safety_agreed(call.from_user.id)
    await call.answer("✅ Qoidalar qabul qilindi")
    try:
        await call.message.delete()  # type: ignore[union-attr]
    except TelegramBadRequest:
        pass

    # Match'ni qayta tekshirish
    matches = await models.get_matches(call.from_user.id)
    match_id = next((m["match_id"] for m in matches if m["user_id"] == partner_id), None)
    if match_id is None:
        await call.message.answer("❌ Bu odam bilan moslik yo'q yoki bekor qilindi.")  # type: ignore
        return

    await _do_start_chat(call, bot, partner_id, match_id)


@router.callback_query(F.data == "safety:cancel")
async def safety_cancelled(call: CallbackQuery) -> None:
    await call.answer("Bekor qilindi")
    if call.message:
        try:
            await call.message.delete()  # type: ignore[union-attr]
        except TelegramBadRequest:
            pass


async def _do_start_chat(
    call: CallbackQuery, bot: Bot, partner_id: int, match_id: int,
) -> None:
    """Haqiqiy chat ochish (safety screen'dan keyin)."""
    if call.from_user is None or call.message is None:
        return

    await models.start_chat(call.from_user.id, partner_id, match_id)
    await log_event(call.from_user.id, EventType.CHAT_STARTED, {"partner": partner_id})

    me = await models.get_user(call.from_user.id)
    name_me = esc(me["name"]) if me else "Foydalanuvchi"

    await call.message.answer(  # type: ignore[union-attr]
        "💬 <b>Anonim suhbat boshlandi.</b>\n"
        "Yozgan xabaringiz to'g'ridan-to'g'ri partneringizga yuboriladi.\n\n"
        "⚠️ Username, telefon raqami, havolalar yuborilsa — avtomatik ogohlantirish.\n\n"
        "Tugatish uchun <b>🔚 Suhbatni tugatish</b>.",
        reply_markup=reply.chat_kb(),
    )
    try:
        await bot.send_message(
            partner_id,
            f"💬 <b>{name_me}</b> siz bilan suhbat boshladi.\n"
            f"Javob yozing — xabaringiz unga yetib boradi.",
            reply_markup=reply.chat_kb(),
        )
    except (TelegramForbiddenError, TelegramBadRequest) as e:
        logger.info("Chat invite to %s failed: %s", partner_id, e)
        await models.stop_chat(call.from_user.id)
        await call.message.answer(  # type: ignore[union-attr]
            "❗️ Partner botni bloklab qo'ygan ko'rinadi. Suhbat ochilmadi.",
            reply_markup=reply.main_menu(),
        )


# ============ 🔚 SUHBATNI TUGATISH ============

@router.message(F.text == "🔚 Suhbatni tugatish")
async def chat_stop(message: Message, bot: Bot) -> None:
    if message.from_user is None:
        return
    partner = await models.stop_chat(message.from_user.id)
    await log_event(message.from_user.id, EventType.CHAT_ENDED, {"partner": partner})

    # Buferlar tozalanadi (RAM tejash)
    chat_buffer.clear(message.from_user.id)
    if partner:
        chat_buffer.clear(partner)

    await message.answer("✅ Suhbat tugatildi.", reply_markup=reply.main_menu())
    if partner:
        try:
            await bot.send_message(
                partner, "ℹ️ Partner suhbatni tugatdi.", reply_markup=reply.main_menu(),
            )
        except (TelegramForbiddenError, TelegramBadRequest):
            pass


# ============ 🚫 SHIKOYAT ============

@router.callback_query(F.data.startswith("report:"))
async def report_from_match(call: CallbackQuery, state: FSMContext) -> None:
    if call.data is None or call.message is None:
        return
    partner_id = int(call.data.split(":", 1)[1])
    await state.set_state(ReportFlow.reason)
    await state.update_data(report_target=partner_id)
    await call.answer()
    await call.message.answer(  # type: ignore[union-attr]
        "Shikoyat sababini tanlang:",
        reply_markup=inline.report_reasons_kb(partner_id),
    )


@router.callback_query(F.data.startswith("reportr:"))
async def report_submit(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if call.data is None or call.from_user is None or call.message is None:
        return
    _, target_str, reason = call.data.split(":", 2)
    target = int(target_str)
    report_id = await models.add_report(call.from_user.id, target, reason)
    await log_event(target, EventType.REPORT_CREATED, {"by": call.from_user.id, "reason": reason})

    # 🆕 Partner'ning xotiradagi oxirgi xabarlarini DB ga saqlaymiz
    partner_messages = chat_buffer.get_messages(target, limit=100)
    if partner_messages:
        saved = await models.save_reported_messages(report_id, target, partner_messages)
        logger.info(
            "Report #%s: saved %s messages from sender=%s", report_id, saved, target,
        )

    await state.clear()
    await call.answer("Shikoyat qabul qilindi.", show_alert=True)
    await call.message.answer(  # type: ignore[union-attr]
        "✅ Shikoyatingiz va xabarlar tarixi adminga yuborildi.\n"
        "Tekshirib chiqishadi.",
        reply_markup=reply.main_menu(),
    )

    count = await models.reports_count(target)
    if count >= 3:
        from config import load_config
        cfg = load_config()
        await models.set_banned(target, True)
        for admin_id in cfg.admin_ids:
            try:
                await bot.send_message(
                    admin_id,
                    f"⚠️ Foydalanuvchi <code>{target}</code> avtomatik bloklandi "
                    f"({count} ta shikoyat to'plandi).",
                )
            except (TelegramForbiddenError, TelegramBadRequest):
                pass


@router.callback_query(F.data == "report_cancel")
async def report_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.answer("Bekor qilindi.")
    if call.message:
        try:
            await call.message.delete()  # type: ignore[union-attr]
        except TelegramBadRequest:
            pass


# ============ XABARLARNI UZATISH (RELAY) — MODERATION BILAN ============

# Asosiy menyu tugmalari — relay qilinmasligi kerak
_MENU_BUTTONS: set[str] = {
    # Asosiy menyu
    "🔍 Qidirish", "👤 Profil", "💌 Mosliklar", "❓ Yordam",
    # Eski tugmalar (backward compat)
    "🔍 Anketalarni ko'rish", "👤 Mening anketam", "💌 Mosliklarim",
    "⚙️ Sozlamalar",
    # Search
    "❤️ Yoqdi", "👎 Yoqmadi", "🚫 Shikoyat",
    "🔙 Bosh sahifa", "🏡 Bosh sahifa", "🏠 Asosiy menyu",
    # Chat
    "🔚 Suhbatni tugatish",
    # Registration / edit
    "❌ Bekor qilish", "✅ Ha, to'g'ri", "🔄 Qayta to'ldirish",
    "⏭ O'tkazib yuborish", "🗑 Bo'sh qoldirish",
    "👨 Erkak", "👩 Ayol", "🌈 Farqi yo'q",
    "📍 Lokatsiya yuborish",
}


async def _check_pre_relay(message: Message) -> tuple[int, str] | None:
    """Pre-relay tekshiruvi: partner mavjudmi, user mute emasmi.
    Returns: (partner_id, "ok") yoki None.
    """
    if message.from_user is None:
        return None

    # Mute tekshiruvi
    if await models.is_muted(message.from_user.id):
        await message.answer(
            "🔇 <b>Siz vaqtinchalik cheklangansiz</b>\n\n"
            "Qoidabuzarlik sababli chat ishlatish huquqidan mahrumsiz. "
            "Birozdan keyin qayta urinib ko'ring.",
        )
        return None

    partner = await models.get_chat_partner(message.from_user.id)
    if not partner:
        return None

    if await models.is_banned(partner):
        await models.stop_chat(message.from_user.id)
        await message.answer(
            "ℹ️ Partner bloklangan. Suhbat tugatildi.",
            reply_markup=reply.main_menu(),
        )
        return None

    return partner, "ok"


async def _moderate_or_relay(
    message: Message, bot: Bot, partner: int,
    text: str = "",
) -> bool:
    """Matnli xabarni filter'dan o'tkazish va kerak bo'lsa moderation.
    Returns: True — moderation amal qildi (relay qilmang), False — toza, relay qiling.
    """
    if not text:
        return False
    violation = detect_violation(text)
    if violation is None:
        return False

    reason, _matched = violation
    result = await handle_violation(message.from_user.id, reason, text)  # type: ignore
    await message.answer(format_action_message(result))

    # Ban bo'lsa, chat ham tugatiladi
    if result.action == "ban":
        await models.stop_chat(message.from_user.id)  # type: ignore
        chat_buffer.clear(message.from_user.id)  # type: ignore
        chat_buffer.clear(partner)

    return True  # relay qilinmaydi


@router.message(F.text & ~F.text.startswith("/"))
async def relay_text(message: Message, bot: Bot) -> None:
    if message.from_user is None or not message.text:
        return
    if message.text in _MENU_BUTTONS:
        return

    res = await _check_pre_relay(message)
    if res is None:
        return
    partner = res[0]

    # 🛡 Filter check
    if await _moderate_or_relay(message, bot, partner, text=message.text):
        return  # filtered

    # Buferga saqlash (RAM)
    chat_buffer.append(message.from_user.id, "text", content=message.text)

    try:
        await bot.send_message(partner, message.text, protect_content=True)
    except (TelegramForbiddenError, TelegramBadRequest) as e:
        logger.info("Relay text to %s failed: %s", partner, e)
        await message.answer("❗️ Partnerga xabar yetkazib bo'lmadi.")


@router.message(F.photo)
async def relay_photo(message: Message, bot: Bot) -> None:
    if message.from_user is None or not message.photo:
        return

    res = await _check_pre_relay(message)
    if res is None:
        return
    partner = res[0]

    # Photo caption ham tekshiriladi
    if message.caption and await _moderate_or_relay(message, bot, partner, text=message.caption):
        return

    photo_id = message.photo[-1].file_id
    chat_buffer.append(message.from_user.id, "photo", content=message.caption or "", file_id=photo_id)
    try:
        await bot.send_photo(
            partner, photo_id, caption=message.caption, protect_content=True,
        )
    except (TelegramForbiddenError, TelegramBadRequest):
        await message.answer("❗️ Rasm yetkazilmadi.")


@router.message(F.voice)
async def relay_voice(message: Message, bot: Bot) -> None:
    if message.from_user is None or not message.voice:
        return
    res = await _check_pre_relay(message)
    if res is None:
        return
    partner = res[0]

    chat_buffer.append(message.from_user.id, "voice", file_id=message.voice.file_id)
    try:
        await bot.send_voice(partner, message.voice.file_id, protect_content=True)
    except (TelegramForbiddenError, TelegramBadRequest):
        await message.answer("❗️ Ovozli xabar yetkazilmadi.")


@router.message(F.video_note)
async def relay_video_note(message: Message, bot: Bot) -> None:
    if message.from_user is None or not message.video_note:
        return
    res = await _check_pre_relay(message)
    if res is None:
        return
    partner = res[0]

    chat_buffer.append(message.from_user.id, "video_note", file_id=message.video_note.file_id)
    try:
        await bot.send_video_note(partner, message.video_note.file_id, protect_content=True)
    except (TelegramForbiddenError, TelegramBadRequest):
        await message.answer("❗️ Video-xabar yetkazilmadi.")


@router.message(F.sticker)
async def relay_sticker(message: Message, bot: Bot) -> None:
    if message.from_user is None or not message.sticker:
        return
    res = await _check_pre_relay(message)
    if res is None:
        return
    partner = res[0]

    chat_buffer.append(message.from_user.id, "sticker", file_id=message.sticker.file_id)
    try:
        await bot.send_sticker(partner, message.sticker.file_id, protect_content=True)
    except (TelegramForbiddenError, TelegramBadRequest):
        pass

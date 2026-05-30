"""Admin Monitoring Dashboard — real-time statistika.

Spec qoidalari:
- N+1 yo'q (bitta SQL aggregate)
- LIMIT har joyda
- Indeksdan foydalanish
"""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from config import Config
from database import alerts, logs, models
from keyboards import inline
from utils.helpers import esc

router = Router(name="admin_monitoring")


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


# ============ MONITORING MENU TUGMASI ============

def _monitoring_menu_kb():
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Real-time Dashboard", callback_data="mon:dash")],
            [InlineKeyboardButton(text="📜 User Timeline", callback_data="mon:tl")],
            [InlineKeyboardButton(text="🚨 Alerts", callback_data="mon:alerts")],
            [InlineKeyboardButton(text="« Admin panelga qaytish", callback_data="adm:back")],
        ]
    )


@router.callback_query(F.data == "mon:menu")
async def mon_menu(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer()
    pending = await alerts.count_pending()
    text = (
        "<b>📊 Monitoring System</b>\n\n"
        f"🚨 Yangi alerts: <b>{pending}</b>\n\n"
        "Bo'limni tanlang:"
    )
    try:
        await call.message.edit_text(text, reply_markup=_monitoring_menu_kb())  # type: ignore
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=_monitoring_menu_kb())  # type: ignore


@router.message(Command("monitoring"))
async def cmd_monitoring(message: Message, config: Config) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    pending = await alerts.count_pending()
    await message.answer(
        f"<b>📊 Monitoring System</b>\n\n"
        f"🚨 Yangi alerts: <b>{pending}</b>\n\nBo'limni tanlang:",
        reply_markup=_monitoring_menu_kb(),
    )


# ============ 📊 REAL-TIME DASHBOARD ============

@router.callback_query(F.data == "mon:dash")
async def mon_dashboard(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer()

    # Bitta query bilan barcha agregatlarni olamiz (no N+1)
    s = await models.detailed_stats()
    pending_alerts = await alerts.count_pending()
    today_events = await logs.get_event_aggregates(since_minutes=24 * 60)

    text = (
        "<b>📊 Real-time Dashboard</b>\n\n"
        f"👥 Total users: <b>{s['total_users']}</b>\n"
        f"🟢 Active (24h): <b>{s['online_24h']}</b>\n"
        f"🟢 Active (7d): <b>{s['online_7d']}</b>\n"
        f"➕ New today: <b>{s['new_today']}</b>\n\n"
        f"❤️ Likes today: <b>{today_events.get(logs.EventType.LIKE_SENT, 0)}</b>\n"
        f"💞 Matches today: <b>{today_events.get(logs.EventType.MATCH_CREATED, 0)}</b>\n"
        f"💬 Active chats: <b>{s['active_chats']}</b>\n"
        f"📝 Profile updates today: <b>{today_events.get(logs.EventType.PROFILE_UPDATED, 0)}</b>\n\n"
        f"⚠️ Reports (pending): <b>{s['pending_reports']}</b>\n"
        f"🚨 Alerts (pending): <b>{pending_alerts}</b>\n"
        f"🚫 Banned: <b>{s['banned_users']}</b>\n"
        f"👁 Shadow-banned: <b>{s['shadow_banned']}</b>"
    )
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="mon:dash")],
        [InlineKeyboardButton(text="« Orqaga", callback_data="mon:menu")],
    ])
    try:
        await call.message.edit_text(text, reply_markup=kb)  # type: ignore
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=kb)  # type: ignore

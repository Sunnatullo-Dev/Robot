"""Admin Alerts UI — shubhali foydalanuvchilarni boshqarish."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from config import Config
from database import admin_logs, alerts, models
from utils.helpers import esc

router = Router(name="admin_alerts")


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


def _alerts_list_kb(items: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for a in items[:15]:
        name = esc(a.get("name") or "—")[:20]
        reason = alerts.REASON_LABELS.get(a["reason"], a["reason"])[:20]
        text = f"🚨 {name} — {reason}"
        rows.append([InlineKeyboardButton(text=text, callback_data=f"alrt:v:{a['id']}")])
    rows.append([InlineKeyboardButton(text="« Orqaga", callback_data="mon:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _alert_actions_kb(alert_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚫 Ban", callback_data=f"alrt:ban:{alert_id}:{user_id}"),
                InlineKeyboardButton(text="👁 Shadowban", callback_data=f"alrt:shadow:{alert_id}:{user_id}"),
            ],
            [InlineKeyboardButton(text="⚠️ Warn (xabar yuborish)", callback_data=f"alrt:warn:{alert_id}:{user_id}")],
            [InlineKeyboardButton(text="✅ Yopish (no-op)", callback_data=f"alrt:resolve:{alert_id}")],
            [InlineKeyboardButton(text="« Orqaga", callback_data="mon:alerts")],
        ]
    )


@router.callback_query(F.data == "mon:alerts")
async def mon_alerts_list(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer()

    pending = await alerts.get_pending_alerts(limit=15)
    if not pending:
        text = "<b>🚨 Alerts</b>\n\n✅ Yangi alert yo'q."
    else:
        text = f"<b>🚨 Pending Alerts ({len(pending)})</b>\n\nKo'rish uchun tanlang:"

    try:
        await call.message.edit_text(text, reply_markup=_alerts_list_kb(pending))  # type: ignore
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=_alerts_list_kb(pending))  # type: ignore


@router.callback_query(F.data.startswith("alrt:v:"))
async def mon_alert_view(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    alert_id = int(call.data.split(":")[-1])  # type: ignore
    a = await alerts.get_alert(alert_id)
    if not a:
        await call.answer("Alert topilmadi", show_alert=True)
        return

    # PENDING → VIEWED
    if a["status"] == alerts.AlertStatus.PENDING:
        await alerts.update_status(alert_id, alerts.AlertStatus.VIEWED)

    user_id = a["user_id"]
    reason = alerts.REASON_LABELS.get(a["reason"], a["reason"])
    uname = f"@{esc(a['username'])}" if a.get("username") else "—"
    name = esc(a.get("name") or "—")

    text = (
        f"<b>🚨 Alert #{alert_id}</b>\n\n"
        f"👤 Foydalanuvchi: <code>{user_id}</code>\n"
        f"Ism: {name}\n"
        f"Username: {uname}\n\n"
        f"⚠️ Sabab: <b>{reason}</b>\n"
        f"📝 Tafsilot: {esc(a.get('details') or '—')}\n"
        f"🕐 Vaqt: {(a['created_at'] or '')[:16]}\n\n"
        f"Holatlar:\n"
        f"  🚫 Bloklangan: {'Ha' if a.get('is_banned') else 'Yo''q'}\n"
        f"  👁 Shadowban: {'Ha' if a.get('is_shadow_banned') else 'Yo''q'}"
    )
    await call.answer()
    try:
        await call.message.edit_text(text, reply_markup=_alert_actions_kb(alert_id, user_id))  # type: ignore
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=_alert_actions_kb(alert_id, user_id))  # type: ignore


@router.callback_query(F.data.startswith("alrt:ban:"))
async def mon_alert_ban(call: CallbackQuery, bot: Bot, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    _, _, alert_str, uid_str = call.data.split(":", 3)  # type: ignore
    alert_id = int(alert_str)
    user_id = int(uid_str)

    await models.set_banned(user_id, True)
    await alerts.update_status(alert_id, alerts.AlertStatus.RESOLVED)
    await admin_logs.log_action(call.from_user.id, admin_logs.AdminAction.BAN, user_id, "from_alert")

    await call.answer("✅ Bloklandi va alert yopildi", show_alert=True)
    try:
        await bot.send_message(user_id, "🚫 Siz administrator tomonidan bloklandingiz.")
    except (TelegramForbiddenError, TelegramBadRequest):
        pass


@router.callback_query(F.data.startswith("alrt:shadow:"))
async def mon_alert_shadow(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    _, _, alert_str, uid_str = call.data.split(":", 3)  # type: ignore
    alert_id = int(alert_str)
    user_id = int(uid_str)

    await models.set_shadow_banned(user_id, True)
    await alerts.update_status(alert_id, alerts.AlertStatus.RESOLVED)
    await admin_logs.log_action(
        call.from_user.id, admin_logs.AdminAction.SHADOWBAN, user_id, "from_alert",
    )
    await call.answer("✅ Shadowban qo'yildi", show_alert=True)


@router.callback_query(F.data.startswith("alrt:warn:"))
async def mon_alert_warn(call: CallbackQuery, bot: Bot, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    _, _, alert_str, uid_str = call.data.split(":", 3)  # type: ignore
    alert_id = int(alert_str)
    user_id = int(uid_str)

    try:
        await bot.send_message(
            user_id,
            "⚠️ <b>Ogohlantirish</b>\n\n"
            "Sizning xatti-harakatlaringiz administratsiya tomonidan "
            "diqqat bilan kuzatilmoqda. Qoidalarga rioya qiling — aks holda "
            "akkauntingiz bloklanishi mumkin.",
        )
    except (TelegramForbiddenError, TelegramBadRequest):
        pass

    await alerts.update_status(alert_id, alerts.AlertStatus.RESOLVED)
    await call.answer("✅ Ogohlantirildi", show_alert=True)


@router.callback_query(F.data.startswith("alrt:resolve:"))
async def mon_alert_resolve(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    alert_id = int(call.data.split(":")[-1])  # type: ignore
    await alerts.update_status(alert_id, alerts.AlertStatus.RESOLVED)
    await call.answer("✅ Yopildi", show_alert=True)

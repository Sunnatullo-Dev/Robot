"""Admin Panel V2 — kengaytirilgan boshqaruv markazi.

Asosiy bo'limlar:
  📊 Dashboard         — real-time statistika
  👥 Foydalanuvchilar  — qidiruv, user card, ban/unban/shadow/delete
  ⚠️ Shikoyatlar       — kutilayotgan shikoyatlar navbati
  📢 Broadcast         — filtered audience (M/F/active/region/all)
  🤖 Sozlamalar        — live edit (auto-ban, min age, daily limit)
  🧪 Test tizimi       — seed/unseed/backup/csv export
  📂 Loglar            — admin amallari tarixi
  ⚙️ Server holati     — bot/DB/system info
"""
from __future__ import annotations

import asyncio
import csv
import io
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    FSInputFile,
    Message,
)

from config import Config
from data.test_users import BASE_ID, TEST_USERS
from database import models
from database.db import get_db_path
from keyboards import inline, reply
from states.user_states import AdminFlow
from utils.helpers import esc

router = Router(name="admin")
logger = logging.getLogger(__name__)

# Bot start vaqti — uptime hisoblash uchun
_BOT_START_TIME = time.monotonic()


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


def _fmt_time(ts: str | None) -> str:
    if not ts:
        return "—"
    return ts[:16].replace("T", " ")


def _format_user_card(u: dict) -> str:
    name = esc(u.get("name")) or "—"
    username = f"@{esc(u['username'])}" if u.get("username") else "—"
    status = "🚫 Banned" if u.get("is_banned") else ("👁 Shadowban" if u.get("is_shadow_banned") else "🟢 Aktiv")
    premium = "💎 Premium" if u.get("premium_until") else "❌ Yo'q"
    return (
        f"<b>👤 Foydalanuvchi #{u['user_id']}</b>\n\n"
        f"Ism: <b>{name}</b>\n"
        f"Username: {username}\n"
        f"Yosh: {u.get('age') or '—'} | Jins: {u.get('gender') or '—'}\n"
        f"Shahar: {esc(u.get('city')) or '—'}\n"
        f"Status: {status}\n"
        f"Premium: {premium}\n"
        f"Ro'yxatdan o'tgan: {_fmt_time(u.get('created_at'))}\n"
        f"Oxirgi faollik: {_fmt_time(u.get('last_seen'))}"
    )


# ============ ASOSIY MENYU ============

@router.message(Command("admin"))
async def admin_panel(message: Message, config: Config) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    await message.answer(
        "<b>🛠 Admin Panel V2</b>\n\n"
        "Boshqaruv markaziga xush kelibsiz.",
        reply_markup=inline.admin_menu_kb(),
    )


@router.callback_query(F.data == "adm:back")
async def adm_back(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer()
    try:
        await call.message.edit_text(  # type: ignore[union-attr]
            "<b>🛠 Admin Panel V2</b>", reply_markup=inline.admin_menu_kb()
        )
    except TelegramBadRequest:
        await call.message.answer(  # type: ignore[union-attr]
            "<b>🛠 Admin Panel V2</b>", reply_markup=inline.admin_menu_kb()
        )


# ============ 📊 DASHBOARD ============

@router.callback_query(F.data == "adm:dashboard")
async def adm_dashboard(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer()
    s = await models.detailed_stats()
    growth = ""
    if s["new_7d"] > 0:
        rate = (s["new_today"] / max(s["new_7d"] / 7, 1)) * 100
        growth = f"\n📈 Bugungi o'sish: {rate:.0f}%"

    top_regions = "\n".join(
        [f"  • {esc(r)} — {c}" for r, c in s["top_regions"]]
    ) or "  • —"

    text = (
        f"<b>📊 Dashboard</b>\n\n"
        f"<b>Foydalanuvchilar:</b>\n"
        f"👥 Jami: <b>{s['total_users']}</b>\n"
        f"📝 Anketali: <b>{s['with_profile']}</b>\n"
        f"🟢 Faol (7 kun): <b>{s['online_7d']}</b>\n"
        f"⚡ Online (24h): <b>{s['online_24h']}</b>\n"
        f"➕ Yangi bugun: <b>{s['new_today']}</b>\n"
        f"📅 Yangi (7 kun): <b>{s['new_7d']}</b>{growth}\n\n"
        f"<b>Aktivlik:</b>\n"
        f"❤️ Like bugun: <b>{s['likes_today']}</b>\n"
        f"❤️ Like jami: <b>{s['total_likes']}</b>\n"
        f"💞 Match bugun: <b>{s['matches_today']}</b>\n"
        f"💞 Match jami: <b>{s['total_matches']}</b>\n"
        f"💬 Faol chatlar: <b>{s['active_chats']}</b>\n\n"
        f"<b>Jins:</b>\n"
        f"👨 Erkak: <b>{s['males']}</b> | 👩 Ayol: <b>{s['females']}</b>\n\n"
        f"<b>Moderatsiya:</b>\n"
        f"🚫 Bloklangan: <b>{s['banned_users']}</b>\n"
        f"👁 Shadowban: <b>{s['shadow_banned']}</b>\n"
        f"⚠️ Yangi shikoyatlar: <b>{s['pending_reports']}</b>\n"
        f"📋 Jami shikoyatlar: <b>{s['total_reports']}</b>\n\n"
        f"<b>🏆 Top 5 viloyat:</b>\n{top_regions}"
    )
    try:
        await call.message.edit_text(text, reply_markup=inline.admin_back_kb())  # type: ignore
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=inline.admin_back_kb())  # type: ignore


# ============ 👥 USER MANAGEMENT ============

@router.callback_query(F.data == "adm:users")
async def adm_users(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer()
    text = (
        "<b>👥 Foydalanuvchilar boshqaruvi</b>\n\n"
        "🔍 Qidirish — ID, @username yoki ism bo'yicha\n"
        "🚫 Ban / ✅ Unban — Telegram ID bo'yicha"
    )
    try:
        await call.message.edit_text(text, reply_markup=inline.admin_users_kb())  # type: ignore
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=inline.admin_users_kb())  # type: ignore


@router.callback_query(F.data == "adm:search")
async def adm_search_start(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AdminFlow.user_search)
    await call.answer()
    await call.message.answer(  # type: ignore
        "🔍 ID, @username yoki ismni yuboring:\n"
        "(Bekor qilish: /cancel)"
    )


@router.message(AdminFlow.user_search, F.text)
async def adm_search_do(message: Message, state: FSMContext, config: Config) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    query = (message.text or "").strip()
    await state.clear()

    users = await models.find_users(query, limit=10)
    if not users:
        await message.answer(f"❌ '{esc(query)}' bo'yicha foydalanuvchi topilmadi.", reply_markup=reply.main_menu())
        return

    if len(users) == 1:
        u = users[0]
        await message.answer(
            _format_user_card(u),
            reply_markup=inline.admin_user_card_kb(
                u["user_id"], bool(u.get("is_banned")), bool(u.get("is_shadow_banned"))
            ),
        )
    else:
        lines = [f"<b>🔎 {len(users)} ta foydalanuvchi topildi:</b>\n"]
        for u in users:
            uname = f"@{esc(u['username'])}" if u.get("username") else ""
            status = "🚫" if u.get("is_banned") else ("👁" if u.get("is_shadow_banned") else "🟢")
            lines.append(f"{status} <code>{u['user_id']}</code> — {esc(u.get('name')) or '—'} {uname}")
        lines.append("\nAniq foydalanuvchini ko'rish uchun ID kiriting va /admin → 🔍 Qidirish.")
        await message.answer("\n".join(lines), reply_markup=reply.main_menu())


@router.callback_query(F.data.startswith("adm:uact:"))
async def adm_user_action(call: CallbackQuery, config: Config, bot: Bot) -> None:
    """Universal user action handler: ban/unban/shadow/unshadow/delete/reports."""
    if call.data is None or call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    _, _, action, uid_str = call.data.split(":", 3)
    user_id = int(uid_str)
    admin_id = call.from_user.id

    if action == "ban":
        await models.set_banned(user_id, True)
        await models.resolve_reports(user_id)
        await models.log_admin_action(admin_id, "ban", user_id)
        await call.answer("✅ Bloklandi", show_alert=True)
        try:
            await bot.send_message(user_id, "🚫 Siz administrator tomonidan bloklandingiz.")
        except (TelegramForbiddenError, TelegramBadRequest):
            pass
    elif action == "unban":
        await models.set_banned(user_id, False)
        await models.log_admin_action(admin_id, "unban", user_id)
        await call.answer("✅ Blokdan chiqarildi", show_alert=True)
    elif action == "shadow":
        await models.set_shadow_banned(user_id, True)
        await models.log_admin_action(admin_id, "shadowban", user_id)
        await call.answer("✅ Shadowban qo'yildi", show_alert=True)
    elif action == "unshadow":
        await models.set_shadow_banned(user_id, False)
        await models.log_admin_action(admin_id, "unshadowban", user_id)
        await call.answer("✅ Shadowban olindi", show_alert=True)
    elif action == "delete":
        await models.hard_delete_user(user_id)
        await models.log_admin_action(admin_id, "delete", user_id)
        await call.answer("✅ Foydalanuvchi to'liq o'chirildi", show_alert=True)
        await call.message.answer(f"🗑 Foydalanuvchi <code>{user_id}</code> bazadan butunlay o'chirildi.")  # type: ignore
        return
    elif action == "reports":
        reports = await models.get_user_reports(user_id)
        if not reports:
            await call.answer("Shikoyatlar yo'q", show_alert=True)
            return
        lines = [f"<b>📜 #{user_id} ga oid shikoyatlar ({len(reports)})</b>\n"]
        for r in reports[:20]:
            lines.append(
                f"• {_fmt_time(r['created_at'])} — "
                f"{esc(r.get('reason') or '—')} (status: {r.get('status') or 'pending'})"
            )
        await call.message.answer("\n".join(lines))  # type: ignore
        return

    # Yangilangan user card ko'rsatish
    u = await models.get_user(user_id)
    if u:
        try:
            await call.message.edit_text(  # type: ignore
                _format_user_card(u),
                reply_markup=inline.admin_user_card_kb(
                    user_id, bool(u.get("is_banned")), bool(u.get("is_shadow_banned"))
                ),
            )
        except TelegramBadRequest:
            pass


# ============ ⚠️ REPORTS QUEUE ============

@router.callback_query(F.data == "adm:reports")
async def adm_reports(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer()
    reports = await models.get_pending_reports()
    if not reports:
        text = "<b>⚠️ Shikoyatlar navbati</b>\n\n✅ Kutilayotgan shikoyatlar yo'q."
    else:
        text = f"<b>⚠️ Shikoyatlar navbati ({len(reports)})</b>\n\nFoydalanuvchini tanlang:"
    try:
        await call.message.edit_text(text, reply_markup=inline.admin_reports_kb(reports))  # type: ignore
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=inline.admin_reports_kb(reports))  # type: ignore


@router.callback_query(F.data.startswith("adm:rpt:"))
async def adm_report_view(call: CallbackQuery, config: Config) -> None:
    if call.data is None or call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    user_id = int(call.data.split(":")[-1])
    await call.answer()

    u = await models.get_user(user_id)
    reports = await models.get_user_reports(user_id)

    if not u:
        await call.message.answer(f"❌ Foydalanuvchi #{user_id} topilmadi.")  # type: ignore
        return

    reasons_text = "\n".join(
        f"  {i+1}. {_fmt_time(r['created_at'])} — {esc(r.get('reason') or '—')}"
        for i, r in enumerate(reports[:10])
    )
    text = (
        _format_user_card(u) +
        f"\n\n<b>⚠️ Shikoyatlar ({len(reports)}):</b>\n{reasons_text}"
    )
    try:
        await call.message.edit_text(text, reply_markup=inline.admin_report_actions_kb(user_id))  # type: ignore
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=inline.admin_report_actions_kb(user_id))  # type: ignore


@router.callback_query(F.data.startswith("adm:rptr:"))
async def adm_report_resolve(call: CallbackQuery, config: Config) -> None:
    if call.data is None or call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    user_id = int(call.data.split(":")[-1])
    n = await models.resolve_reports(user_id)
    await models.log_admin_action(call.from_user.id, "reports_resolve", user_id, f"count={n}")
    await call.answer(f"✅ {n} ta shikoyat yopildi", show_alert=True)
    # Reports menusiga qaytamiz
    await adm_reports(call, config)


# ============ 📢 BROADCAST ============

@router.callback_query(F.data == "adm:broadcast_menu")
async def adm_broadcast_menu(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer()
    try:
        await call.message.edit_text(  # type: ignore
            "<b>📢 Broadcast — qabul qiluvchini tanlang:</b>",
            reply_markup=inline.admin_broadcast_filter_kb(),
        )
    except TelegramBadRequest:
        await call.message.answer(
            "<b>📢 Broadcast — qabul qiluvchini tanlang:</b>",
            reply_markup=inline.admin_broadcast_filter_kb(),
        )  # type: ignore


@router.callback_query(F.data.startswith("adm:bcast:"))
async def adm_broadcast_pick_audience(
    call: CallbackQuery, state: FSMContext, config: Config,
) -> None:
    if call.data is None or call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    audience = call.data.split(":")[-1]  # all/male/female/active/region
    await call.answer()

    if audience == "region":
        await state.set_state(AdminFlow.broadcast_filter_region)
        await call.message.answer(  # type: ignore
            "🏙 Viloyat nomini kiriting (qisqartirilgan ham ishlaydi, masalan 'Toshkent'):",
            reply_markup=reply.cancel_kb(),
        )
        return

    await state.update_data(audience=audience, region="")
    await state.set_state(AdminFlow.broadcast)
    await call.message.answer(  # type: ignore
        f"📤 <b>Yuboriladigan xabarni yuboring</b> (matn/rasm/video/forward).\n"
        f"Qabul qiluvchi: <b>{_audience_label(audience)}</b>\n\n"
        f"Bekor qilish: /cancel",
        reply_markup=reply.cancel_kb(),
    )


def _audience_label(a: str) -> str:
    return {
        "all": "Hammasi",
        "male": "Faqat erkaklar",
        "female": "Faqat ayollar",
        "active": "Faollar (7 kun)",
        "region": "Viloyat bo'yicha",
        "premium": "Premium",
    }.get(a, a)


@router.message(AdminFlow.broadcast_filter_region, F.text)
async def adm_broadcast_region_input(
    message: Message, state: FSMContext, config: Config,
) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=reply.main_menu())
        return
    region = (message.text or "").strip()
    await state.update_data(audience="region", region=region)
    await state.set_state(AdminFlow.broadcast)
    await message.answer(
        f"📤 Yuboriladigan xabarni yuboring.\n"
        f"Viloyat: <b>{esc(region)}</b>",
        reply_markup=reply.cancel_kb(),
    )


@router.message(AdminFlow.broadcast, F.text == "❌ Bekor qilish")
async def adm_broadcast_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=reply.main_menu())


@router.message(AdminFlow.broadcast)
async def adm_broadcast_send(
    message: Message, state: FSMContext, bot: Bot, config: Config,
) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return

    data = await state.get_data()
    audience = data.get("audience", "all")
    region = data.get("region", "")
    await state.clear()

    ids = await models.get_audience_ids(audience, region)
    if not ids:
        await message.answer("📭 Hech kim topilmadi.", reply_markup=reply.main_menu())
        return

    sent, failed = 0, 0
    status = await message.answer(f"📤 Yuborilmoqda... 0/{len(ids)} ({_audience_label(audience)})")
    from_chat = message.chat.id
    msg_id = message.message_id

    for i, uid in enumerate(ids, 1):
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=from_chat, message_id=msg_id)
            sent += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.copy_message(chat_id=uid, from_chat_id=from_chat, message_id=msg_id)
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
                await status.edit_text(f"📤 {i}/{len(ids)} — ✅{sent} ❌{failed}")
            except TelegramBadRequest:
                pass
        await asyncio.sleep(0.04)

    await models.log_admin_action(
        message.from_user.id, "broadcast", details=f"audience={audience} sent={sent} failed={failed}",
    )

    final = (
        f"✅ <b>Tarqatish tugadi</b>\n\n"
        f"Qabul qiluvchi: {_audience_label(audience)}\n"
        f"Yetkazildi: <b>{sent}</b>\n"
        f"Xato: <b>{failed}</b>"
    )
    try:
        await status.edit_text(final)
    except TelegramBadRequest:
        await message.answer(final)


# ============ 🤖 BOT SETTINGS ============

@router.callback_query(F.data == "adm:settings")
async def adm_settings(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer()
    settings = await models.get_all_settings()
    text = (
        "<b>🤖 Bot sozlamalari</b>\n\n"
        "✅/❌ tugmalar — yoqish/o'chirish\n"
        "Raqamlar — bosing va yangi qiymat kiriting"
    )
    try:
        await call.message.edit_text(text, reply_markup=inline.admin_settings_kb(settings))  # type: ignore
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=inline.admin_settings_kb(settings))  # type: ignore


@router.callback_query(F.data.startswith("adm:set_toggle:"))
async def adm_settings_toggle(call: CallbackQuery, config: Config) -> None:
    if call.data is None or call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    key = call.data.split(":")[-1]
    current = await models.get_setting(key, "0")
    new_value = "0" if current == "1" else "1"
    await models.set_setting(key, new_value)
    await models.log_admin_action(call.from_user.id, "setting_toggle", details=f"{key}={new_value}")
    await call.answer(f"✅ {key} = {new_value}")
    await adm_settings(call, config)


@router.callback_query(F.data.startswith("adm:set_edit:"))
async def adm_settings_edit_start(
    call: CallbackQuery, state: FSMContext, config: Config,
) -> None:
    if call.data is None or call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    key = call.data.split(":")[-1]
    await state.set_state(AdminFlow.setting_value)
    await state.update_data(setting_key=key)
    await call.answer()
    await call.message.answer(  # type: ignore
        f"⚙️ <b>{key}</b> uchun yangi qiymat kiriting (raqam):"
    )


@router.message(AdminFlow.setting_value, F.text)
async def adm_settings_edit_save(
    message: Message, state: FSMContext, config: Config,
) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("❗️ Faqat raqam yuboring.")
        return
    data = await state.get_data()
    key = data.get("setting_key", "")
    await models.set_setting(key, text)
    await models.log_admin_action(message.from_user.id, "setting_edit", details=f"{key}={text}")
    await state.clear()
    await message.answer(f"✅ <b>{key}</b> = <code>{text}</code>", reply_markup=reply.main_menu())


# ============ 🧪 DEV TOOLS ============

@router.callback_query(F.data == "adm:devtools")
async def adm_devtools(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer()
    try:
        await call.message.edit_text(  # type: ignore
            "<b>🧪 Test va Dev tizimi</b>",
            reply_markup=inline.admin_devtools_kb(),
        )
    except TelegramBadRequest:
        await call.message.answer(
            "<b>🧪 Test va Dev tizimi</b>",
            reply_markup=inline.admin_devtools_kb(),
        )  # type: ignore


@router.callback_query(F.data == "adm:dev:seed")
async def adm_dev_seed(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AdminFlow.seed_photo)
    await call.answer()
    await call.message.answer(  # type: ignore
        f"📸 Bitta rasm yuboring — u {len(TEST_USERS)} ta test anketada ishlatiladi.\n"
        f"(Yoki terminal'da: <code>python -m tools.seed</code>)\n\n"
        f"Bekor qilish: /cancel",
        reply_markup=reply.cancel_kb(),
    )


@router.callback_query(F.data == "adm:dev:unseed")
async def adm_dev_unseed(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    deleted = await models.delete_seed_users(BASE_ID)
    await models.log_admin_action(call.from_user.id, "unseed", details=f"count={deleted}")
    await call.answer(f"🗑 {deleted} ta test anketa o'chirildi", show_alert=True)


@router.callback_query(F.data == "adm:dev:backup")
async def adm_dev_backup(call: CallbackQuery, bot: Bot, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer("Backup tayyorlanmoqda...")
    src = get_db_path()
    if not os.path.exists(src):
        await call.message.answer("❌ DB fayli topilmadi.")  # type: ignore
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"{src}.{ts}.bak"
    shutil.copyfile(src, bak)
    try:
        await bot.send_document(
            call.from_user.id, FSInputFile(bak), caption=f"💾 DB Backup ({ts})"
        )
        os.remove(bak)
        await models.log_admin_action(call.from_user.id, "db_backup")
    except Exception as e:
        logger.exception("Backup send failed: %s", e)
        await call.message.answer(f"❗️ Yuborib bo'lmadi: {e}\nFayl: <code>{bak}</code>")  # type: ignore


@router.callback_query(F.data == "adm:dev:csv")
async def adm_dev_csv(call: CallbackQuery, bot: Bot, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer("CSV tayyorlanmoqda...")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "user_id", "username", "name", "age", "gender", "looking_for",
        "city", "bio", "latitude", "longitude",
        "is_active", "is_banned", "is_shadow_banned",
        "created_at", "last_seen",
    ])

    import aiosqlite
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute(
            "SELECT user_id, username, name, age, gender, looking_for, "
            "city, bio, latitude, longitude, is_active, is_banned, "
            "is_shadow_banned, created_at, last_seen FROM users"
        ) as cur:
            async for row in cur:
                writer.writerow(row)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    data = buf.getvalue().encode("utf-8")
    await bot.send_document(
        call.from_user.id,
        BufferedInputFile(data, filename=f"users_{ts}.csv"),
        caption=f"📤 Users export ({ts})",
    )
    await models.log_admin_action(call.from_user.id, "csv_export")


# ============ 📂 LOGS ============

@router.callback_query(F.data == "adm:logs")
async def adm_logs(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer()
    logs = await models.get_admin_logs(limit=30)
    if not logs:
        text = "<b>📂 Admin loglari</b>\n\nLog yo'q."
    else:
        lines = ["<b>📂 So'nggi 30 ta admin amali:</b>\n"]
        for l in logs:
            target = f" → #{l['target_id']}" if l.get("target_id") else ""
            details = f" ({esc(l['details'])})" if l.get("details") else ""
            lines.append(f"• {_fmt_time(l['created_at'])} | admin <code>{l['admin_id']}</code>: <b>{l['action']}</b>{target}{details}")
        text = "\n".join(lines)
    try:
        await call.message.edit_text(text, reply_markup=inline.admin_back_kb())  # type: ignore
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=inline.admin_back_kb())  # type: ignore


# ============ ⚙️ SERVER STATUS ============

@router.callback_query(F.data == "adm:server")
async def adm_server(call: CallbackQuery, bot: Bot, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.answer()

    # Bot info
    me = await bot.get_me()
    uptime_sec = time.monotonic() - _BOT_START_TIME
    hours = int(uptime_sec // 3600)
    mins = int((uptime_sec % 3600) // 60)

    # DB file
    db_path = get_db_path()
    db_size = os.path.getsize(db_path) / (1024 * 1024) if os.path.exists(db_path) else 0

    # System info (psutil bo'lmasdan ham)
    py_version = sys.version.split()[0]

    text = (
        f"<b>⚙️ Server holati</b>\n\n"
        f"<b>Bot:</b>\n"
        f"🟢 Online: @{esc(me.username)} (#{me.id})\n"
        f"⏱ Uptime: <b>{hours} soat {mins} daqiqa</b>\n"
        f"🐍 Python: <code>{py_version}</code>\n\n"
        f"<b>Ma'lumotlar bazasi:</b>\n"
        f"📁 Yo'l: <code>{db_path}</code>\n"
        f"💾 Hajm: <b>{db_size:.2f} MB</b>\n\n"
        f"<b>Adminlar:</b> {len(config.admin_ids)} ta"
    )
    try:
        await call.message.edit_text(text, reply_markup=inline.admin_back_kb())  # type: ignore
    except TelegramBadRequest:
        await call.message.answer(text, reply_markup=inline.admin_back_kb())  # type: ignore


# ============ Legacy Ban/Unban (FSM by ID) ============

@router.callback_query(F.data == "adm:ban")
async def admin_ban_start(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AdminFlow.ban_user)
    await call.answer()
    await call.message.answer("Ban qilinadigan foydalanuvchi ID sini yuboring:", reply_markup=reply.cancel_kb())  # type: ignore


@router.callback_query(F.data == "adm:unban")
async def admin_unban_start(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AdminFlow.unban_user)
    await call.answer()
    await call.message.answer("Unban qilinadigan foydalanuvchi ID sini yuboring:", reply_markup=reply.cancel_kb())  # type: ignore


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
    target_id = int(text)
    await models.set_banned(target_id, True)
    await models.log_admin_action(message.from_user.id, "ban", target_id)
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
    target_id = int(text)
    await models.set_banned(target_id, False)
    await models.log_admin_action(message.from_user.id, "unban", target_id)
    await state.clear()
    await message.answer(f"✅ <code>{text}</code> blokdan chiqarildi.", reply_markup=reply.main_menu())


# ============ /stats, /seed, /unseed buyruqlari (avvalgi) ============

@router.message(Command("stats"))
async def cmd_stats(message: Message, config: Config) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    s = await models.detailed_stats()
    await message.answer(
        f"👥 {s['total_users']} | 🟢 {s['active_users']} | "
        f"💞 {s['total_matches']} | ⚠️ {s['pending_reports']} pending"
    )


@router.message(Command("seed"))
async def cmd_seed_start(
    message: Message, state: FSMContext, config: Config,
) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    await state.set_state(AdminFlow.seed_photo)
    await message.answer(
        f"📸 Bitta rasm yuboring — u {len(TEST_USERS)} ta test "
        f"anketada ishlatiladi.\n\nBekor qilish: /cancel",
        reply_markup=reply.cancel_kb(),
    )


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
    for i, (gender, name, age, lf, city, bio, lat, lng) in enumerate(TEST_USERS):
        user_id = BASE_ID + i + 1
        try:
            await models.upsert_seed_user(
                user_id=user_id, name=name, age=age, gender=gender,
                looking_for=lf, city=city, bio=bio, photo_id=photo_id,
                latitude=lat, longitude=lng,
            )
            created += 1
        except Exception as e:
            logger.exception("Seed user %s failed: %s", name, e)

    await models.log_admin_action(message.from_user.id, "seed", details=f"count={created}")
    await state.clear()
    await message.answer(
        f"✅ <b>{created} ta test anketa yaratildi</b>\n\n"
        f"O'chirish: /unseed",
        reply_markup=reply.main_menu(),
    )


@router.message(AdminFlow.seed_photo)
async def seed_no_photo(message: Message) -> None:
    await message.answer("❗️ Iltimos, rasm yuboring (matn yoki fayl emas).")


@router.message(Command("unseed"))
async def cmd_unseed(message: Message, config: Config) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    deleted = await models.delete_seed_users(BASE_ID)
    await models.log_admin_action(message.from_user.id, "unseed", details=f"count={deleted}")
    await message.answer(
        f"🗑 {deleted} ta test anketa o'chirildi.",
        reply_markup=reply.main_menu(),
    )

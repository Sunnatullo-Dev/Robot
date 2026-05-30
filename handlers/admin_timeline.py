"""User Timeline — foydalanuvchining barcha event'larini ko'rish (pagination)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import Config
from database import logs
from states.user_states import AdminFlow
from utils.helpers import esc

router = Router(name="admin_timeline")

PAGE_SIZE = 50  # Bir sahifada nechta event


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


def _timeline_kb(user_id: int, page: int, total: int) -> InlineKeyboardMarkup:
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    has_prev = page > 0
    has_next = (page + 1) < total_pages

    nav_row: list[InlineKeyboardButton] = []
    if has_prev:
        nav_row.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"tl:p:{user_id}:{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if has_next:
        nav_row.append(InlineKeyboardButton(text="▶️ Next", callback_data=f"tl:p:{user_id}:{page+1}"))

    return InlineKeyboardMarkup(inline_keyboard=[
        nav_row,
        [InlineKeyboardButton(text="« Orqaga", callback_data="mon:menu")],
    ])


def _format_timeline(events: list[dict], page: int, total: int) -> str:
    if not events:
        return "📭 Bu foydalanuvchi uchun event'lar topilmadi."

    start_idx = page * PAGE_SIZE + 1
    lines = [f"<b>📜 Timeline (jami {total})</b>\n"]
    for i, e in enumerate(events, start=start_idx):
        label = logs.EVENT_LABELS.get(e["event_type"], e["event_type"])
        ts = (e.get("created_at") or "")[:16].replace("T", " ")
        meta = e.get("metadata")
        meta_str = ""
        if isinstance(meta, dict) and meta:
            # Faqat kalit-qiymat preview
            pairs = [f"{k}={v}" for k, v in list(meta.items())[:3]]
            meta_str = " — " + ", ".join(pairs)
        lines.append(f"{ts} | {label}{esc(meta_str)}")
    return "\n".join(lines)


# Asosiy menyu — User ID so'rovi
@router.callback_query(F.data == "mon:tl")
async def mon_tl_start(call: CallbackQuery, state: FSMContext, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AdminFlow.user_search)
    await state.update_data(search_purpose="timeline")
    await call.answer()
    await call.message.answer(  # type: ignore
        "📜 <b>User Timeline</b>\n\n"
        "Telegram ID yuboring (masalan: <code>123456789</code>):\n\n"
        "Bekor qilish: /cancel"
    )


# Kiritilgan ID bo'yicha timeline
@router.message(AdminFlow.user_search, F.text)
async def mon_tl_show(message: Message, state: FSMContext, config: Config) -> None:
    if message.from_user is None or not _is_admin(message.from_user.id, config):
        return
    data = await state.get_data()
    if data.get("search_purpose") != "timeline":
        return  # admin_monitoring qidiruvi emas

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("❗️ Faqat raqam (Telegram ID) yuboring.")
        return

    user_id = int(text)
    await state.clear()

    total = await logs.count_user_events(user_id)
    events = await logs.get_user_timeline(user_id, limit=PAGE_SIZE, offset=0)
    body = _format_timeline(events, page=0, total=total)
    await message.answer(body, reply_markup=_timeline_kb(user_id, 0, total))


# Pagination
@router.callback_query(F.data.startswith("tl:p:"))
async def mon_tl_page(call: CallbackQuery, config: Config) -> None:
    if call.from_user is None or not _is_admin(call.from_user.id, config):
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    _, _, uid_str, page_str = call.data.split(":", 3)  # type: ignore
    user_id = int(uid_str)
    page = int(page_str)

    total = await logs.count_user_events(user_id)
    events = await logs.get_user_timeline(
        user_id, limit=PAGE_SIZE, offset=page * PAGE_SIZE,
    )
    body = _format_timeline(events, page=page, total=total)
    await call.answer()
    try:
        await call.message.edit_text(  # type: ignore
            body, reply_markup=_timeline_kb(user_id, page, total),
        )
    except TelegramBadRequest:
        await call.message.answer(  # type: ignore
            body, reply_markup=_timeline_kb(user_id, page, total),
        )


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery) -> None:
    await call.answer()

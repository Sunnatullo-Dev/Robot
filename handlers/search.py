import logging
from typing import Any

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import models
from database.logs import EventType
from keyboards import inline, reply
from services.logging_service import log_event
from services.watermark import get_watermarked_photo
from states.user_states import ReportFlow
from utils.helpers import esc, format_profile

router = Router(name="search")
logger = logging.getLogger(__name__)


async def _show_next(message: Message, state: FSMContext, user_id: int, bot: Bot) -> None:
    candidate = await models.get_next_candidate(user_id)

    # ENDLESS FEED: agar yangi anketa qolmagan bo'lsa:
    # 1) Dislike'larni reset → barcha "yoqmadi" bosilganlar qayta ko'rsatiladi
    # 2) Hali ham bo'sh bo'lsa, match bo'lmagan like'larni ham reset
    if not candidate:
        reset_count = await models.reset_dislikes(user_id)
        if reset_count > 0:
            candidate = await models.get_next_candidate(user_id)

    if not candidate:
        reset_count = await models.reset_pending_likes(user_id)
        if reset_count > 0:
            candidate = await models.get_next_candidate(user_id)

    if not candidate:
        # Haqiqatan ham hech kim yo'q (bo'sh DB)
        await state.update_data(current_candidate=None)
        matches_count = len(await models.get_matches(user_id))
        match_line = f"\n💞 Mosliklaringiz: <b>{matches_count}</b>" if matches_count else ""
        await message.answer(
            "📭 <b>Hozircha bo'shroq</b>\n\n"
            "Yangi a'zolar har kuni qo'shilib turadi — "
            "biroz vaqtdan keyin qaytib keling 🌅" +
            match_line,
            reply_markup=reply.main_menu(),
        )
        return

    await state.update_data(current_candidate=candidate["user_id"])
    distance = candidate.pop("_distance", None)

    # Deterrent watermark — "TARQATISH TAQIQLANADI" + "Tanishuv Bot — Anonim"
    # Shaxsiy ma'lumot YO'Q. Screenshot olinsa ham, ogohlantirish ko'rinadi.
    photo_to_send: Any = candidate["photo_id"]
    wm = await get_watermarked_photo(bot, candidate["photo_id"])
    if wm is not None:
        photo_to_send = wm

    await message.answer_photo(
        photo=photo_to_send,
        caption=format_profile(candidate, distance_km=distance),
        reply_markup=inline.candidate_dm_kb(candidate["user_id"]),
        protect_content=True,
    )
    # Ovozli bio bo'lsa, qo'shimcha xabar
    if candidate.get("voice_id"):
        try:
            await message.answer_voice(
                candidate["voice_id"],
                caption="🎤 Ovozli salomlashish",
                protect_content=True,
            )
        except Exception:
            pass


@router.message(Command("search"))
@router.message(F.text == "🔍 Qidirish")
@router.message(F.text == "🔍 Anketalarni ko'rish")  # eski nom (backward compat)
async def start_search(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.from_user is None:
        return
    user = await models.get_user(message.from_user.id)
    if not user or not user.get("photo_id"):
        await message.answer(
            "Avval o'z anketangizni yarating. /start bosing.",
            reply_markup=reply.main_menu(),
        )
        return
    # Reply keyboardni o'rnatamiz (❤️ 👎 🚫 🏠) — keyingi photo'lar inline tugmali bo'ladi
    await message.answer("🔍 <b>Qidiruv boshlandi</b>", reply_markup=reply.search_kb())
    await _show_next(message, state, message.from_user.id, bot)


@router.message(F.text == "❤️ Yoqdi")
async def like(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.from_user is None:
        return
    data = await state.get_data()
    target = data.get("current_candidate")
    if not target:
        await _show_next(message, state, message.from_user.id, bot)
        return

    is_match = await models.add_like(message.from_user.id, target, True)
    await log_event(message.from_user.id, EventType.LIKE_SENT, {"to": target})
    me = await models.get_user(message.from_user.id)
    target_user = await models.get_user(target)

    if is_match and me and target_user:
        # Mutual match — har ikkalasiga match xabari
        await log_event(message.from_user.id, EventType.MATCH_CREATED, {"with": target})
        await log_event(target, EventType.MATCH_CREATED, {"with": message.from_user.id})
        t_name = esc(target_user["name"])
        my_name = esc(me["name"])

        await message.answer(
            f"💞 <b>Mos keldi!</b>\n\n"
            f"<b>{t_name}</b> ham sizni yoqtirdi 🎉",
            reply_markup=inline.chat_start_only_kb(target),
        )
        try:
            await bot.send_message(
                target,
                f"💞 <b>Mos keldi!</b>\n\n"
                f"<b>{my_name}</b> sizni yoqtirdi 🎉",
                reply_markup=inline.chat_start_only_kb(message.from_user.id),
            )
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.info("Match notify failed for %s: %s", target, e)
    elif me and target_user and target_user.get("photo_id"):
        # ONE-WAY LIKE — target hali like bosmagan, lekin notification yuboramiz
        # Target 'Suhbat boshlash' bosib, like'ni qaytarib match yaratishi mumkin
        try:
            caption = (
                f"❤️ <b>Yangi like!</b>\n\n"
                f"<b>{esc(me['name'])}</b>, {me.get('age') or '—'} yosh\n"
                f"🏙 {esc(me.get('city') or '—')}\n"
            )
            if me.get("bio"):
                caption += f"\n💬 {esc(me['bio'])}\n"
            caption += "\nSuhbatlashmoqchimisiz?"

            await bot.send_photo(
                target,
                photo=me["photo_id"],
                caption=caption,
                reply_markup=inline.like_response_kb(message.from_user.id),
                protect_content=True,
            )
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.info("Like notify failed for %s: %s", target, e)

    await _show_next(message, state, message.from_user.id, bot)


# ============ LIKE NOTIFICATION RESPONSE ============

@router.callback_query(F.data.startswith("likeresp:chat:"))
async def like_response_chat(call: CallbackQuery, bot: Bot) -> None:
    """Foydalanuvchi like notification ostidagi 'Suhbat boshlash' tugmasini bosdi.
    Bu like'ni qaytarish va match yaratishni anglatadi.
    """
    if call.data is None or call.from_user is None or call.message is None:
        return
    liker_id = int(call.data.split(":")[2])
    me_id = call.from_user.id

    # Auto-like back (B → A) → match yaratiladi (A → B avval bo'lgan)
    is_match = await models.add_like(me_id, liker_id, True)
    await log_event(me_id, EventType.LIKE_SENT, {"to": liker_id})

    if is_match:
        await log_event(me_id, EventType.MATCH_CREATED, {"with": liker_id})
        await log_event(liker_id, EventType.MATCH_CREATED, {"with": me_id})

    await call.answer("✅ Match yaratildi!", show_alert=False)

    # Eski like notification'ni o'chirib, yangi xabar yuboramiz
    try:
        await call.message.delete()  # type: ignore[union-attr]
    except TelegramBadRequest:
        pass

    # Like yuborgan tomonga (A) xabar yuboramiz
    me_user = await models.get_user(me_id)
    if me_user:
        try:
            await bot.send_message(
                liker_id,
                f"💞 <b>Mos keldi!</b>\n\n"
                f"<b>{esc(me_user['name'])}</b> ham sizni yoqtirdi 🎉",
                reply_markup=inline.chat_start_only_kb(me_id),
            )
        except (TelegramForbiddenError, TelegramBadRequest):
            pass

    # B'ga (caller) chat boshlash tugmasi
    await call.message.answer(  # type: ignore[union-attr]
        f"💞 <b>Mos keldi!</b>\n\nSuhbat boshlash uchun tugmani bosing:",
        reply_markup=inline.chat_start_only_kb(liker_id),
    )


@router.callback_query(F.data.startswith("likeresp:no:"))
async def like_response_no(call: CallbackQuery) -> None:
    """Foydalanuvchi like notification'da 'Yoqmadi' bossin."""
    if call.data is None or call.from_user is None or call.message is None:
        return
    liker_id = int(call.data.split(":")[2])

    # Dislike B → A
    await models.add_like(call.from_user.id, liker_id, False)
    await log_event(call.from_user.id, EventType.DISLIKE_SENT, {"to": liker_id})

    await call.answer("👎 Inkor etildi")
    try:
        await call.message.delete()  # type: ignore[union-attr]
    except TelegramBadRequest:
        pass


@router.message(F.text == "👎 Yoqmadi")
async def dislike(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.from_user is None:
        return
    data = await state.get_data()
    target = data.get("current_candidate")
    if target:
        await models.add_like(message.from_user.id, target, False)
        await log_event(message.from_user.id, EventType.DISLIKE_SENT, {"to": target})
    await _show_next(message, state, message.from_user.id, bot)


@router.message(F.text == "🚫 Shikoyat")
async def report_start(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    target = data.get("current_candidate")
    if not target:
        await message.answer("Hozir hech kimga shikoyat qila olmaysiz.", reply_markup=reply.main_menu())
        return
    await state.set_state(ReportFlow.reason)
    await state.update_data(report_target=target)
    await message.answer(
        "Shikoyat sababini tanlang:",
        reply_markup=inline.report_reasons_kb(target),
    )

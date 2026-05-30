import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import models
from database.logs import EventType
from keyboards import inline, reply
from services.logging_service import log_event
from states.user_states import ReportFlow
from utils.helpers import esc, format_profile

router = Router(name="search")
logger = logging.getLogger(__name__)


async def _show_next(message: Message, state: FSMContext, user_id: int) -> None:
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
    # Anketa rasmi ostida inline tugma "💌 Lichkaga o'tish"
    # protect_content=True — forward va save'ni bloklaydi
    await message.answer_photo(
        photo=candidate["photo_id"],
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
async def start_search(message: Message, state: FSMContext) -> None:
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
    await _show_next(message, state, message.from_user.id)


@router.message(F.text == "❤️ Yoqdi")
async def like(message: Message, state: FSMContext, bot: Bot) -> None:
    if message.from_user is None:
        return
    data = await state.get_data()
    target = data.get("current_candidate")
    if not target:
        await _show_next(message, state, message.from_user.id)
        return

    is_match = await models.add_like(message.from_user.id, target, True)
    await log_event(message.from_user.id, EventType.LIKE_SENT, {"to": target})
    me = await models.get_user(message.from_user.id)
    target_user = await models.get_user(target)

    if is_match and me and target_user:
        await log_event(message.from_user.id, EventType.MATCH_CREATED, {"with": target})
        await log_event(target, EventType.MATCH_CREATED, {"with": message.from_user.id})
        my_uname = f"@{esc(me['username'])}" if me.get("username") else "—"
        t_uname = f"@{esc(target_user['username'])}" if target_user.get("username") else "—"
        my_name = esc(me["name"])
        t_name = esc(target_user["name"])

        await message.answer(
            f"💞 <b>Mos keldi!</b>\n\n"
            f"<b>{t_name}</b> ham sizni yoqtirdi 🎉\n"
            f"Username: {t_uname}",
            reply_markup=inline.match_actions_kb(target),
        )
        try:
            await bot.send_message(
                target,
                f"💞 <b>Mos keldi!</b>\n\n"
                f"<b>{my_name}</b> sizni yoqtirdi 🎉\n"
                f"Username: {my_uname}",
                reply_markup=inline.match_actions_kb(message.from_user.id),
            )
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.info("Match notify failed for %s: %s", target, e)

    await _show_next(message, state, message.from_user.id)


@router.message(F.text == "👎 Yoqmadi")
async def dislike(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    data = await state.get_data()
    target = data.get("current_candidate")
    if target:
        await models.add_like(message.from_user.id, target, False)
        await log_event(message.from_user.id, EventType.DISLIKE_SENT, {"to": target})
    await _show_next(message, state, message.from_user.id)


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

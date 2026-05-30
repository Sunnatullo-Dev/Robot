import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import models
from keyboards import inline, reply
from states.user_states import ReportFlow
from utils.helpers import esc, format_profile

router = Router(name="search")
logger = logging.getLogger(__name__)


async def _show_next(message: Message, state: FSMContext, user_id: int) -> None:
    candidate = await models.get_next_candidate(user_id)
    if not candidate:
        await state.update_data(current_candidate=None)
        # Statistika
        matches_count = len(await models.get_matches(user_id))
        match_line = f"\n💞 Mosliklaringiz: <b>{matches_count}</b>" if matches_count else ""
        await message.answer(
            "🎯 <b>Siz hammasini ko'rib chiqdingiz!</b>\n\n"
            "Yangi a'zolar har kuni qo'shilib turadi — "
            "ertaga qaytib keling 🌅" +
            match_line,
            reply_markup=reply.main_menu(),
        )
        return

    await state.update_data(current_candidate=candidate["user_id"])
    distance = candidate.pop("_distance", None)
    await message.answer_photo(
        photo=candidate["photo_id"],
        caption=format_profile(candidate, distance_km=distance),
        reply_markup=reply.search_kb(),
    )


@router.message(Command("search"))
@router.message(F.text == "🔍 Anketalarni ko'rish")
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
    me = await models.get_user(message.from_user.id)
    target_user = await models.get_user(target)

    if is_match and me and target_user:
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

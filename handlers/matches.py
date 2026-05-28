from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from database import models
from keyboards import inline, reply
from utils.helpers import format_profile

router = Router(name="matches")


@router.message(Command("matches"))
@router.message(F.text == "💌 Mosliklarim")
async def show_matches(message: Message) -> None:
    if message.from_user is None:
        return
    matches = await models.get_matches(message.from_user.id)
    if not matches:
        await message.answer(
            "Sizda hali hech qanday moslik yo'q.\n"
            "Anketalarni ko'rib, yoqqanlariga ❤️ bosing — kimdir sizni ham yoqtirsa, "
            "shu yerda paydo bo'ladi.",
            reply_markup=reply.main_menu(),
        )
        return

    await message.answer(
        f"💌 <b>Sizda {len(matches)} ta moslik bor:</b>",
        reply_markup=inline.matches_kb(matches),
    )


@router.callback_query(F.data.startswith("match_view:"))
async def view_match(call: CallbackQuery) -> None:
    if call.data is None or call.message is None:
        return
    partner_id = int(call.data.split(":", 1)[1])
    partner = await models.get_user(partner_id)
    await call.answer()
    if not partner:
        await call.message.answer("Foydalanuvchi topilmadi.")  # type: ignore[union-attr]
        return

    uname = f"@{partner['username']}" if partner.get("username") else "(yashirin)"
    caption = (
        f"{format_profile(partner)}\n\n"
        f"Telegram: {uname}"
    )
    await call.message.answer_photo(  # type: ignore[union-attr]
        photo=partner["photo_id"],
        caption=caption,
        reply_markup=inline.match_actions_kb(partner_id),
    )


@router.callback_query(F.data == "matches_back")
async def back_to_matches(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    matches = await models.get_matches(call.from_user.id)
    await call.answer()
    if not matches:
        await call.message.answer("Mosliklar yo'q.", reply_markup=reply.main_menu())  # type: ignore[union-attr]
        return
    await call.message.answer(  # type: ignore[union-attr]
        f"💌 <b>Sizda {len(matches)} ta moslik bor:</b>",
        reply_markup=inline.matches_kb(matches),
    )


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery) -> None:
    await call.answer()

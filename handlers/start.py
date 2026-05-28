from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import models
from keyboards import reply
from states.user_states import Registration

router = Router(name="start")


WELCOME_TEXT = (
    "👋 Salom, <b>{name}</b>!\n\n"
    "Bu yerda yangi do'stlar topishingiz, suhbatlashishingiz va "
    "balki haqiqiy munosabatlar boshlashingiz mumkin.\n\n"
    "🔒 Sizning ma'lumotlaringiz xavfsiz. Tomonlar bir-birini "
    "<b>like</b> bosgandagina ulanish ochiladi.\n\n"
    "Boshlash uchun anketa yarataylik."
)

HELP_TEXT = (
    "<b>📖 Yordam</b>\n\n"
    "🔍 <b>Anketalarni ko'rish</b> — yangi odamlarni topish\n"
    "👤 <b>Mening anketam</b> — o'z anketangizni ko'rish/tahrirlash\n"
    "💌 <b>Mosliklarim</b> — match bo'lganlar bilan suhbat\n"
    "⚙️ <b>Sozlamalar</b> — anketani o'chirish/yangilash\n\n"
    "<b>Buyruqlar:</b>\n"
    "/start — botni qayta ishga tushirish\n"
    "/profile — o'z anketam\n"
    "/search — qidirishni boshlash\n"
    "/matches — mosliklarim\n"
    "/help — yordam\n\n"
    "❗️ Qoidalarni buzgan foydalanuvchilar bloklanadi."
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if user is None:
        return

    await models.create_or_update_user(user.id, user.username)

    if await models.is_banned(user.id):
        await message.answer("🚫 Siz botdan foydalanish huquqidan mahrum etilgansiz.")
        return

    profile = await models.get_user(user.id)
    if profile and profile.get("photo_id"):
        await message.answer(
            f"Xush kelibsiz, <b>{profile['name']}</b>!",
            reply_markup=reply.main_menu(),
        )
        return

    await message.answer(
        WELCOME_TEXT.format(name=user.first_name or "do'stim"),
        reply_markup=reply.remove,
    )
    await message.answer("📝 Ismingizni kiriting:", reply_markup=reply.cancel_kb())
    await state.set_state(Registration.name)


@router.message(Command("help"))
@router.message(F.text == "❓ Yordam")
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=reply.main_menu())


@router.message(F.text == "🏠 Asosiy menyu")
async def to_main_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🏠 Asosiy menyu", reply_markup=reply.main_menu())


@router.message(F.text == "❌ Bekor qilish")
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=reply.main_menu())

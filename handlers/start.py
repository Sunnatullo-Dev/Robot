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
    "Bu yerda yangi do'stlar va, balki, hayotingizning sherigini ham "
    "topishingiz mumkin.\n\n"
    "<b>✨ Qanday ishlaydi:</b>\n"
    "1️⃣ Anketa to'ldirasiz\n"
    "2️⃣ Boshqalarni ko'rasiz\n"
    "3️⃣ Yoqqanlariga ❤️ bosasiz\n"
    "4️⃣ Mos kelsangiz — anonim yozishasiz\n\n"
    "🔒 Sizning ma'lumotlaringiz xavfsiz. Telefon raqamingizni "
    "hech kim ko'ra olmaydi.\n\n"
    "Boshlaymizmi? ⬇️"
)

WELCOME_BACK_TEXT = (
    "👋 Xush kelibsiz, <b>{name}</b>!\n\n"
    "Pastdagi tugmalardan birini tanlang:"
)

ONBOARDING_TIP = (
    "🎉 <b>Anketangiz tayyor!</b>\n\n"
    "📌 <b>Kichik maslahatlar:</b>\n"
    "• ❤️ — yoqsa\n"
    "• 👎 — yoqmasa (anonim, hech kim bilmaydi)\n"
    "• Ikki tomon ham ❤️ bossa — mos kelasiz 💞\n"
    "• Anonim yozishasiz — raqamingiz hech kimga bermaydi\n\n"
    "🚀 Boshlash uchun pastdagi <b>🔍 Qidirish</b> tugmasini bosing."
)

HELP_TEXT = (
    "<b>📖 Qisqacha qo'llanma</b>\n\n"
    "<b>🔍 QIDIRISH</b>\n"
    "Anketalarni ko'rasiz va <b>❤️</b> yoki <b>👎</b> bosasiz\n\n"
    "<b>💞 MATCH</b>\n"
    "Ikki tomon ❤️ bossa, sizlar mos kelasiz va "
    "anonim suhbat boshlash mumkin\n\n"
    "<b>👤 PROFIL</b>\n"
    "Ism, yosh, shahar, rasm va boshqalarni o'zgartirish\n\n"
    "<b>📋 Buyruqlar:</b>\n"
    "/start — botni qayta ishga tushirish\n"
    "/search — qidirish\n"
    "/profile — mening anketam\n"
    "/matches — mosliklarim\n"
    "/cancel — joriy amalni bekor qilish\n\n"
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
            WELCOME_BACK_TEXT.format(name=profile["name"]),
            reply_markup=reply.main_menu(),
        )
        return

    await message.answer(
        WELCOME_TEXT.format(name=user.first_name or "do'stim"),
        reply_markup=reply.remove,
    )
    await message.answer(
        "<b>📝 Anketa: 1/7</b>\n\nIsmingizni kiriting:",
        reply_markup=reply.cancel_kb(),
    )
    await state.set_state(Registration.name)


@router.message(Command("help"))
@router.message(F.text == "❓ Yordam")
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=reply.main_menu())


@router.message(F.text == "🏠 Asosiy menyu")
async def to_main_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🏠 Asosiy menyu", reply_markup=reply.main_menu())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Har qanday FSM holatidan chiqib, asosiy menyuga qaytish."""
    current = await state.get_state()
    await state.clear()
    if current is not None:
        await message.answer(
            "❌ Joriy amal bekor qilindi.",
            reply_markup=reply.main_menu(),
        )
    else:
        await message.answer(
            "Bekor qilish uchun hech narsa yo'q.",
            reply_markup=reply.main_menu(),
        )


@router.message(F.text == "❌ Bekor qilish")
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=reply.main_menu())

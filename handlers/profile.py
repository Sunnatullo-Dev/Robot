from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import models
from keyboards import inline, reply
from states.user_states import EditProfile
from utils.helpers import format_profile, parse_age

router = Router(name="profile")


@router.message(StateFilter(EditProfile), F.text == "❌ Bekor qilish")
async def edit_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=reply.main_menu())


async def _send_profile(message: Message, user_id: int) -> None:
    user = await models.get_user(user_id)
    if not user or not user.get("photo_id"):
        await message.answer(
            "Sizda hali anketa yo'q. /start buyrug'i orqali yarating.",
            reply_markup=reply.main_menu(),
        )
        return
    await message.answer_photo(
        photo=user["photo_id"],
        caption=f"<b>👤 Sizning anketangiz</b>\n\n{format_profile(user)}",
        reply_markup=inline.edit_profile_kb(),
    )


@router.message(Command("profile"))
@router.message(F.text == "👤 Mening anketam")
async def show_profile(message: Message) -> None:
    if message.from_user is None:
        return
    await _send_profile(message, message.from_user.id)


@router.message(F.text == "⚙️ Sozlamalar")
async def settings(message: Message) -> None:
    if message.from_user is None:
        return
    await _send_profile(message, message.from_user.id)


@router.callback_query(F.data.startswith("edit:"))
async def edit_callback(call: CallbackQuery, state: FSMContext) -> None:
    if call.data is None or call.from_user is None:
        return
    field = call.data.split(":", 1)[1]
    await call.answer()

    if field == "delete":
        await models.update_field(call.from_user.id, "is_active", 0)
        await call.message.answer(  # type: ignore[union-attr]
            "🗑 Anketangiz o'chirildi. Qayta yaratish uchun /start bosing.",
            reply_markup=reply.remove,
        )
        return

    prompts = {
        "name": ("📝 Yangi ism:", EditProfile.name, reply.cancel_kb()),
        "age": ("🎂 Yangi yosh (14-99):", EditProfile.age, reply.cancel_kb()),
        "city": ("🏙 Yangi shahar:", EditProfile.city, reply.cancel_kb()),
        "bio": ("💬 Yangi bio:", EditProfile.bio, reply.skip_kb("🗑 Bo'sh qoldirish")),
        "photo": ("📷 Yangi rasm yuboring:", EditProfile.photo, reply.cancel_kb()),
        "looking_for": ("💕 Kimni qidirasiz?", EditProfile.looking_for, reply.looking_for_kb()),
    }
    if field not in prompts:
        return
    text, st, kb = prompts[field]
    await call.message.answer(text, reply_markup=kb)  # type: ignore[union-attr]
    await state.set_state(st)


@router.message(EditProfile.name, F.text)
async def edit_name(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    name = (message.text or "").strip()
    if len(name) < 2 or len(name) > 30:
        await message.answer("❗️ Ism 2 dan 30 belgigacha bo'lsin.")
        return
    await models.update_field(message.from_user.id, "name", name)
    await state.clear()
    await message.answer("✅ Ism yangilandi.", reply_markup=reply.main_menu())


@router.message(EditProfile.age, F.text)
async def edit_age(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    age = parse_age(message.text or "")
    if age is None:
        await message.answer("❗️ 14 dan 99 gacha son kiriting.")
        return
    await models.update_field(message.from_user.id, "age", age)
    await state.clear()
    await message.answer("✅ Yosh yangilandi.", reply_markup=reply.main_menu())


@router.message(EditProfile.city, F.text)
async def edit_city(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    city = (message.text or "").strip()
    if len(city) < 2 or len(city) > 40:
        await message.answer("❗️ Shahar nomi 2 dan 40 belgigacha bo'lsin.")
        return
    await models.update_field(message.from_user.id, "city", city)
    await state.clear()
    await message.answer("✅ Shahar yangilandi.", reply_markup=reply.main_menu())


@router.message(EditProfile.bio, F.text)
async def edit_bio(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    text = (message.text or "").strip()
    bio = "" if text == "🗑 Bo'sh qoldirish" else text[:300]
    await models.update_field(message.from_user.id, "bio", bio)
    await state.clear()
    await message.answer("✅ Bio yangilandi.", reply_markup=reply.main_menu())


@router.message(EditProfile.photo, F.photo)
async def edit_photo(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not message.photo:
        return
    await models.update_field(message.from_user.id, "photo_id", message.photo[-1].file_id)
    await state.clear()
    await message.answer("✅ Rasm yangilandi.", reply_markup=reply.main_menu())


@router.message(EditProfile.looking_for, F.text)
async def edit_looking_for(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    text = message.text or ""
    if "Erkak" in text:
        lf = "M"
    elif "Ayol" in text:
        lf = "F"
    elif "Farqi" in text:
        lf = "A"
    else:
        await message.answer("❗️ Tugmalardan birini tanlang.")
        return
    await models.update_field(message.from_user.id, "looking_for", lf)
    await state.clear()
    await message.answer("✅ Qidiruv yo'nalishi yangilandi.", reply_markup=reply.main_menu())

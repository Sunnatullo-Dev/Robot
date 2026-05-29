import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from data.regions import get_district, get_region
from database import models
from keyboards import inline, reply
from states.user_states import Registration
from utils.helpers import format_profile, parse_age

router = Router(name="registration")
logger = logging.getLogger(__name__)


@router.message(StateFilter(Registration), F.text == "❌ Bekor qilish")
async def reg_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Bekor qilindi. Anketani qayta yaratish uchun /start bosing.",
        reply_markup=reply.main_menu(),
    )


@router.message(Registration.name, F.text)
async def reg_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2 or len(name) > 30:
        await message.answer("❗️ Ism 2 dan 30 belgigacha bo'lsin. Qayta kiriting:")
        return
    await state.update_data(name=name)
    await message.answer("🎂 Yoshingizni kiriting (14-99):")
    await state.set_state(Registration.age)


@router.message(Registration.age, F.text)
async def reg_age(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    age = parse_age(text)
    if age is None:
        await message.answer("❗️ Iltimos, 14 dan 99 gacha bo'lgan son kiriting:")
        return
    await state.update_data(age=age)
    await message.answer("⚧ Jinsingizni tanlang:", reply_markup=reply.gender_kb())
    await state.set_state(Registration.gender)


@router.message(Registration.gender, F.text)
async def reg_gender(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    if "Erkak" in text:
        gender = "M"
        looking_for = "F"  # Erkaklar — ayollarni qidirishadi
    elif "Ayol" in text:
        gender = "F"
        looking_for = "M"  # Ayollar — erkaklarni qidirishadi
    else:
        await message.answer("❗️ Tugmalardan birini tanlang.")
        return
    await state.update_data(gender=gender, looking_for=looking_for)
    await message.answer(
        "🏙 <b>Viloyatingizni tanlang:</b>",
        reply_markup=inline.regions_kb("reg"),
    )
    await state.set_state(Registration.city)


@router.callback_query(Registration.city, F.data.startswith("reg:r:"))
async def reg_region(call: CallbackQuery, state: FSMContext) -> None:
    logger.info("reg_region called: data=%s", call.data)
    if call.data is None or call.message is None:
        return
    idx = int(call.data.split(":")[2])
    region = get_region(idx)
    if not region:
        await call.answer("Viloyat topilmadi.", show_alert=True)
        return
    await call.answer()
    try:
        await call.message.edit_text(  # type: ignore[union-attr]
            f"🏙 <b>{region['name']}</b>\nTuman/shaharni tanlang:",
            reply_markup=inline.districts_kb("reg", idx),
        )
    except Exception as e:
        logger.exception("reg_region edit_text FAILED: %s", e)
        await call.message.answer(  # type: ignore[union-attr]
            f"🏙 <b>{region['name']}</b>\nTuman/shaharni tanlang:",
            reply_markup=inline.districts_kb("reg", idx),
        )


@router.callback_query(Registration.city, F.data == "reg:back")
async def reg_back_regions(call: CallbackQuery) -> None:
    if call.message is None:
        return
    await call.answer()
    await call.message.edit_text(  # type: ignore[union-attr]
        "🏙 <b>Viloyatingizni tanlang:</b>",
        reply_markup=inline.regions_kb("reg"),
    )


@router.callback_query(Registration.city, F.data.startswith("reg:c:"))
async def reg_city_pick(call: CallbackQuery, state: FSMContext) -> None:
    if call.data is None or call.message is None:
        return
    parts = call.data.split(":")
    region_idx, district_idx = int(parts[2]), int(parts[3])
    region = get_region(region_idx)
    district = get_district(region_idx, district_idx)
    if not region or not district:
        await call.answer("Topilmadi.", show_alert=True)
        return
    city = f"{region['name']}, {district}"
    await state.update_data(city=city)
    await call.answer(f"✓ {district}")
    await call.message.edit_text(f"🏙 Tanlandi: <b>{city}</b>")  # type: ignore[union-attr]
    await call.message.answer(  # type: ignore[union-attr]
        "📍 <b>Lokatsiyangizni yuboring</b> (ixtiyoriy)\n\n"
        "Bu yaqin atrofdagi odamlarni topishga yordam beradi.\n"
        "Telefondan: tugmani bosing → ruxsat bering → joriy joylashuv yuboriladi.\n\n"
        "Agar xohlamasangiz «O'tkazib yuborish» bosing.",
        reply_markup=reply.location_kb(),
    )
    await state.set_state(Registration.location)


@router.message(Registration.location, F.location)
async def reg_location(message: Message, state: FSMContext) -> None:
    if message.location is None:
        return
    await state.update_data(
        latitude=message.location.latitude,
        longitude=message.location.longitude,
    )
    await message.answer("✅ Lokatsiya saqlandi.", reply_markup=reply.remove)
    await message.answer(
        "💬 O'zingiz haqingizda qisqacha yozing (yoki o'tkazib yuboring):",
        reply_markup=reply.skip_kb(),
    )
    await state.set_state(Registration.bio)


@router.message(Registration.location, F.text == "⏭ O'tkazib yuborish")
async def reg_skip_location(message: Message, state: FSMContext) -> None:
    await state.update_data(latitude=None, longitude=None)
    await message.answer(
        "💬 O'zingiz haqingizda qisqacha yozing (yoki o'tkazib yuboring):",
        reply_markup=reply.skip_kb(),
    )
    await state.set_state(Registration.bio)


@router.message(Registration.bio, F.text)
async def reg_bio(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    bio = "" if text == "⏭ O'tkazib yuborish" else text[:300]
    await state.update_data(bio=bio)
    await message.answer(
        "📷 Endi o'z rasmingizni yuboring (1 dona):",
        reply_markup=reply.cancel_kb(),
    )
    await state.set_state(Registration.photo)


@router.message(Registration.photo, F.photo)
async def reg_photo(message: Message, state: FSMContext) -> None:
    if not message.photo:
        return
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    data = await state.get_data()

    preview = {
        "name": data.get("name"),
        "age": data.get("age"),
        "gender": data.get("gender"),
        "city": data.get("city"),
        "bio": data.get("bio"),
    }
    await message.answer_photo(
        photo=photo_id,
        caption=f"<b>Anketangizni tasdiqlaysizmi?</b>\n\n{format_profile(preview)}",
        reply_markup=reply.confirm_kb(),
    )
    await state.set_state(Registration.confirm)


@router.message(Registration.photo)
async def reg_photo_invalid(message: Message) -> None:
    await message.answer("❗️ Iltimos, rasm yuboring (fayl/dokument emas).")


@router.message(Registration.confirm, F.text == "✅ Ha, to'g'ri")
async def reg_confirm(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    data = await state.get_data()
    await models.save_profile(
        user_id=message.from_user.id,
        name=data["name"],
        age=data["age"],
        gender=data["gender"],
        looking_for=data["looking_for"],
        city=data["city"],
        bio=data.get("bio", ""),
        photo_id=data["photo_id"],
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
    )
    await state.clear()
    await message.answer(
        "🎉 Tabriklaymiz! Anketangiz tayyor.\n\n"
        "Endi <b>🔍 Anketalarni ko'rish</b> tugmasini bosib, yangi do'stlar topishingiz mumkin.",
        reply_markup=reply.main_menu(),
    )


@router.message(Registration.confirm, F.text == "🔄 Qayta to'ldirish")
async def reg_restart(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("📝 Yangidan boshladik. Ismingizni kiriting:", reply_markup=reply.cancel_kb())
    await state.set_state(Registration.name)

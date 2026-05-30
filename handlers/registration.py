from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from data.regions import get_district, get_region
from database import models
from database.logs import EventType
from keyboards import inline, reply
from services.logging_service import log_event
from states.user_states import Registration
from utils.helpers import format_profile, parse_age

router = Router(name="registration")


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
        await message.answer(
            "🤔 Iltimos, qisqaroq ism kiriting.\n"
            "Ism kamida 2, ko'pi 30 ta belgi bo'lishi kerak.\n"
            "Masalan: <i>Sardor, Aziza</i>"
        )
        return
    await state.update_data(name=name)
    await message.answer("<b>📝 Anketa: 2/7</b>\n\n🎂 Yoshingizni kiriting (masalan: 22):")
    await state.set_state(Registration.age)


@router.message(Registration.age, F.text)
async def reg_age(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    age = parse_age(text)
    if age is None:
        await message.answer(
            "🤔 Iltimos faqat raqam kiriting.\n"
            "Yoshingiz 14 dan 99 gacha bo'lishi kerak."
        )
        return
    await state.update_data(age=age)
    await message.answer(
        "<b>📝 Anketa: 3/7</b>\n\n⚧ Jinsingizni tanlang:",
        reply_markup=reply.gender_kb(),
    )
    await state.set_state(Registration.gender)


@router.message(Registration.gender, F.text)
async def reg_gender(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    if "Erkak" in text:
        gender = "M"
        looking_for = "F"
    elif "Ayol" in text:
        gender = "F"
        looking_for = "M"
    else:
        await message.answer("🤔 Iltimos pastdagi tugmalardan birini tanlang.")
        return
    await state.update_data(gender=gender, looking_for=looking_for)
    await message.answer(
        "<b>📝 Anketa: 4/7</b>\n\n🏙 <b>Viloyatingizni tanlang:</b>",
        reply_markup=inline.regions_kb("reg"),
    )
    await state.set_state(Registration.city)


@router.callback_query(Registration.city, F.data.startswith("reg:r:"))
async def reg_region(call: CallbackQuery, state: FSMContext) -> None:
    if call.data is None or call.message is None:
        return
    idx = int(call.data.split(":")[2])
    region = get_region(idx)
    if not region:
        await call.answer("Viloyat topilmadi.", show_alert=True)
        return
    await call.answer()
    from aiogram.exceptions import TelegramBadRequest
    try:
        await call.message.edit_text(  # type: ignore[union-attr]
            f"🏙 <b>{region['name']}</b>\nTuman/shaharni tanlang:",
            reply_markup=inline.districts_kb("reg", idx),
        )
    except TelegramBadRequest:
        # Eski xabar tahrirlanmasa, yangisini yuboramiz
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
        "<b>📝 Anketa: 5/7</b>\n\n"
        "📍 <b>Lokatsiyangizni yuboring</b> <i>(ixtiyoriy)</i>\n\n"
        "Bu yaqin atrofdagi odamlarni topishga yordam beradi.\n"
        "Telefon: tugmani bosing → ruxsat bering → joriy joylashuv yuboriladi.\n\n"
        "Xohlamasangiz <b>⏭ O'tkazib yuborish</b> bosing.",
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
        "<b>📝 Anketa: 6/7</b>\n\n"
        "💬 O'zingiz haqingizda qisqacha yozing <i>(ixtiyoriy)</i>\n"
        "Masalan: <i>Sport bilan shug'ullanaman, kitob o'qishni yoqtiraman</i>",
        reply_markup=reply.skip_kb(),
    )
    await state.set_state(Registration.bio)


@router.message(Registration.location, F.text == "⏭ O'tkazib yuborish")
async def reg_skip_location(message: Message, state: FSMContext) -> None:
    await state.update_data(latitude=None, longitude=None)
    await message.answer(
        "<b>📝 Anketa: 6/7</b>\n\n"
        "💬 O'zingiz haqingizda qisqacha yozing <i>(ixtiyoriy)</i>\n"
        "Masalan: <i>Sport bilan shug'ullanaman, kitob o'qishni yoqtiraman</i>",
        reply_markup=reply.skip_kb(),
    )
    await state.set_state(Registration.bio)


@router.message(Registration.bio, F.text)
async def reg_bio(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    bio = "" if text == "⏭ O'tkazib yuborish" else text[:300]
    await state.update_data(bio=bio)
    await message.answer(
        "<b>📝 Anketa: 7/7 — oxirgi qadam!</b>\n\n"
        "📷 Endi o'z rasmingizni yuboring.\n"
        "Yaxshi rasm — yaxshi mosliklar kafolati! 😊",
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
    await log_event(
        message.from_user.id,
        EventType.USER_REGISTER,
        metadata={"age": data["age"], "gender": data["gender"], "city": data["city"]},
    )
    await state.clear()
    await message.answer(
        "🎉 <b>Anketangiz tayyor!</b>\n\n"
        "📌 <b>Kichik maslahatlar:</b>\n"
        "• ❤️ — yoqsa\n"
        "• 👎 — yoqmasa (anonim, hech kim bilmaydi)\n"
        "• Ikki tomon ham ❤️ bossa — mos kelasiz 💞\n"
        "• Bot orqali anonim yozishasiz — raqamingiz ko'rinmaydi\n\n"
        "🚀 Boshlash uchun pastdagi <b>🔍 Qidirish</b> tugmasini bosing.",
        reply_markup=reply.main_menu(),
    )


@router.message(Registration.confirm, F.text == "🔄 Qayta to'ldirish")
async def reg_restart(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("📝 Yangidan boshladik. Ismingizni kiriting:", reply_markup=reply.cancel_kb())
    await state.set_state(Registration.name)

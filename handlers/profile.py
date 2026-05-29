import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from data.regions import get_district, get_region
from database import models
from keyboards import inline, reply
from states.user_states import EditProfile
from utils.helpers import format_profile, parse_age

router = Router(name="profile")
logger = logging.getLogger(__name__)


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
    logger.info("edit_callback: data=%s user=%s", call.data, call.from_user.id if call.from_user else None)
    if call.data is None or call.from_user is None:
        logger.warning("edit_callback: early return data/user None")
        return
    field = call.data.split(":", 1)[1]
    await call.answer()

    if field == "delete":
        try:
            await models.update_field(call.from_user.id, "is_active", 0)
            await call.message.answer(  # type: ignore[union-attr]
                "🗑 Anketangiz o'chirildi. Qayta yaratish uchun /start bosing.",
                reply_markup=reply.remove,
            )
            logger.info("edit_callback delete: OK")
        except Exception as e:
            logger.exception("edit_callback delete FAILED: %s", e)
            await call.message.answer(f"❗️ Xatolik: {e}")  # type: ignore[union-attr]
        return

    if field == "city":
        await call.message.answer(  # type: ignore[union-attr]
            "🏙 <b>Viloyatingizni tanlang:</b>",
            reply_markup=inline.regions_kb("edit"),
        )
        await state.set_state(EditProfile.city)
        return

    if field == "location":
        await call.message.answer(  # type: ignore[union-attr]
            "📍 <b>Yangi lokatsiya yuboring</b>\n\n"
            "Tugmani bosib, ruxsat bering. Yoki «O'tkazib yuborish» bilan lokatsiyani o'chirish.",
            reply_markup=reply.location_kb(),
        )
        await state.set_state(EditProfile.location)
        return

    prompts = {
        "name": ("📝 Yangi ism:", EditProfile.name, reply.cancel_kb()),
        "age": ("🎂 Yangi yosh (14-99):", EditProfile.age, reply.cancel_kb()),
        "bio": ("💬 Yangi bio:", EditProfile.bio, reply.skip_kb("🗑 Bo'sh qoldirish")),
        "photo": ("📷 Yangi rasm yuboring:", EditProfile.photo, reply.cancel_kb()),
    }
    if field not in prompts:
        return
    text, st, kb = prompts[field]
    await call.message.answer(text, reply_markup=kb)  # type: ignore[union-attr]
    await state.set_state(st)


@router.callback_query(EditProfile.city, F.data.startswith("edit:r:"))
async def edit_region(call: CallbackQuery) -> None:
    if call.data is None or call.message is None:
        return
    idx = int(call.data.split(":")[2])
    region = get_region(idx)
    if not region:
        await call.answer("Viloyat topilmadi.", show_alert=True)
        return
    await call.answer()
    await call.message.edit_text(  # type: ignore[union-attr]
        f"🏙 <b>{region['name']}</b>\nTuman/shaharni tanlang:",
        reply_markup=inline.districts_kb("edit", idx),
    )


@router.callback_query(EditProfile.city, F.data == "edit:back")
async def edit_back_regions(call: CallbackQuery) -> None:
    if call.message is None:
        return
    await call.answer()
    await call.message.edit_text(  # type: ignore[union-attr]
        "🏙 <b>Viloyatingizni tanlang:</b>",
        reply_markup=inline.regions_kb("edit"),
    )


@router.callback_query(EditProfile.city, F.data.startswith("edit:c:"))
async def edit_city_pick(call: CallbackQuery, state: FSMContext) -> None:
    if call.data is None or call.from_user is None or call.message is None:
        return
    parts = call.data.split(":")
    region_idx, district_idx = int(parts[2]), int(parts[3])
    region = get_region(region_idx)
    district = get_district(region_idx, district_idx)
    if not region or not district:
        await call.answer("Topilmadi.", show_alert=True)
        return
    city = f"{region['name']}, {district}"
    await models.update_field(call.from_user.id, "city", city)
    await state.clear()
    await call.answer(f"✓ {district}")
    await call.message.edit_text(f"✅ Shahar yangilandi: <b>{city}</b>")  # type: ignore[union-attr]
    await call.message.answer("Asosiy menyu", reply_markup=reply.main_menu())  # type: ignore[union-attr]


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


@router.message(EditProfile.location, F.location)
async def edit_location(message: Message, state: FSMContext) -> None:
    if message.from_user is None or message.location is None:
        return
    await models.update_location(
        message.from_user.id,
        message.location.latitude,
        message.location.longitude,
    )
    await state.clear()
    await message.answer("✅ Lokatsiya yangilandi.", reply_markup=reply.main_menu())


@router.message(EditProfile.location, F.text == "⏭ O'tkazib yuborish")
async def edit_location_clear(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    await models.update_location(message.from_user.id, None, None)
    await state.clear()
    await message.answer("✅ Lokatsiya o'chirildi.", reply_markup=reply.main_menu())



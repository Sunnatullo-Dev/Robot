"""Premium paywall — lichkaga o'tish uchun premium sotib olish.

Ish jarayoni:
1. Foydalanuvchi anketa tagidagi "💌 Lichkaga o'tish" tugmasini bosadi
2. Agar Premium yo'q bo'lsa, paywall (narx + karta) ko'rsatiladi
3. "📸 To'lov chekini yuborish" bosib, screenshot/photo yuboradi
4. Bot chekni barcha adminlarga forward qiladi + tasdiqlash buyrug'i
5. Admin /setpremium <user_id> <kunlar> orqali tasdiqlaydi
"""
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Config
from database import models
from keyboards import inline, reply
from states.user_states import PremiumFlow
from utils.helpers import esc

router = Router(name="premium")
logger = logging.getLogger(__name__)


def _paywall_text(config: Config) -> str:
    return (
        "🔒 <b>Premium kerak</b>\n\n"
        "Bu xizmat istalgan foydalanuvchining Telegram lichkasiga "
        "to'g'ridan-to'g'ri o'tish imkoniyatini beradi.\n\n"
        "💎 <b>Premium afzalliklari:</b>\n"
        "• Istalgan odamning Telegram'iga to'g'ridan o'tish\n"
        "• Anketada 💎 belgisi (boshqalar sizni ko'radi)\n"
        "• Maxsus broadcast'larni olish\n"
        "• Yangi imkoniyatlar (kelajakda)\n\n"
        f"💰 <b>Narxi: {esc(config.premium_price)} / {config.premium_days} kun</b>\n"
        f"💳 Karta: <code>{esc(config.premium_card)}</code>\n\n"
        "📸 To'lovni amalga oshirgach, chekni quyidagi tugma orqali yuboring:"
    )


# ============ 💌 LICHKAGA O'TISH ============

@router.callback_query(F.data.startswith("dm:"))
async def dm_request(call: CallbackQuery, config: Config) -> None:
    if call.data is None or call.from_user is None or call.message is None:
        return
    partner_id = int(call.data.split(":")[1])

    is_prem = await models.is_premium(call.from_user.id)

    # Adminlar har doim premium bo'lib hisoblanadi
    if call.from_user.id in config.admin_ids:
        is_prem = True

    if is_prem:
        partner = await models.get_user(partner_id)
        if not partner:
            await call.answer("Foydalanuvchi topilmadi.", show_alert=True)
            return
        await call.answer()
        username = partner.get("username")
        text = (
            f"💌 <b>{esc(partner.get('name')) or 'Foydalanuvchi'}</b>\n\n"
            f"Telegram'i: " + (f"@{esc(username)}" if username else "yashirin")
        )
        await call.message.answer(  # type: ignore[union-attr]
            text,
            reply_markup=inline.open_chat_kb(username, partner_id),
        )
        return

    # Premium yo'q — paywall
    await call.answer()
    await call.message.answer(  # type: ignore[union-attr]
        _paywall_text(config),
        reply_markup=inline.premium_paywall_kb(),
    )


# ============ 📸 TO'LOV CHEKI ============

@router.callback_query(F.data == "prem:paid")
async def prem_paid_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.message is None:
        return
    await state.set_state(PremiumFlow.waiting_receipt)
    await call.answer()
    await call.message.answer(  # type: ignore[union-attr]
        "📸 <b>To'lov chekini yuboring</b>\n\n"
        "Banki ilovasidan screenshot oling va shu chatga yuboring.\n"
        "Admin tekshirib chiqadi (odatda 1 soat ichida) va premium statusingizni yoqadi.\n\n"
        "Bekor qilish: /cancel",
        reply_markup=reply.cancel_kb(),
    )


@router.callback_query(F.data == "prem:cancel")
async def prem_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.answer("Bekor qilindi")
    if call.message:
        try:
            await call.message.delete()  # type: ignore[union-attr]
        except TelegramBadRequest:
            pass


@router.message(PremiumFlow.waiting_receipt, F.text == "❌ Bekor qilish")
async def prem_paid_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=reply.main_menu())


@router.message(PremiumFlow.waiting_receipt, F.photo | F.document)
async def prem_paid_receipt(
    message: Message, state: FSMContext, bot: Bot, config: Config,
) -> None:
    if message.from_user is None:
        return
    user = message.from_user
    uname = f"@{user.username}" if user.username else "—"

    # Adminlarga yuborish
    notify_caption = (
        f"💰 <b>Premium so'rov</b>\n\n"
        f"Foydalanuvchi: <code>{user.id}</code>\n"
        f"Ism: {esc(user.first_name or '')} {esc(user.last_name or '')}\n"
        f"Username: {esc(uname)}\n\n"
        f"Narxi: <b>{esc(config.premium_price)} / {config.premium_days} kun</b>"
    )

    approval_kb = inline.premium_approval_kb(user.id, config.premium_days)

    sent_to = 0
    for admin_id in config.admin_ids:
        try:
            # Chek va boshqaruv tugmalari bir xabarda
            if message.photo:
                await bot.send_photo(
                    admin_id,
                    message.photo[-1].file_id,
                    caption=notify_caption,
                    reply_markup=approval_kb,
                )
            elif message.document:
                await bot.send_document(
                    admin_id,
                    message.document.file_id,
                    caption=notify_caption,
                    reply_markup=approval_kb,
                )
            else:
                await bot.send_message(
                    admin_id,
                    notify_caption,
                    reply_markup=approval_kb,
                )
            sent_to += 1
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.info("Premium notify to %s failed: %s", admin_id, e)

    await state.clear()
    if sent_to > 0:
        await message.answer(
            "✅ <b>Chekingiz adminga yuborildi</b>\n\n"
            "Tekshirilgach (odatda 1 soat ichida) premium statusingiz yoqiladi.\n"
            "Shoshilinch holatlarda admin'ga to'g'ridan-to'g'ri yozing.",
            reply_markup=reply.main_menu(),
        )
    else:
        await message.answer(
            "❗️ Adminlarga yetkazib bo'lmadi. Iltimos keyinroq urinib ko'ring "
            "yoki adminga to'g'ridan-to'g'ri yozing.",
            reply_markup=reply.main_menu(),
        )


@router.message(PremiumFlow.waiting_receipt)
async def prem_paid_other(message: Message) -> None:
    await message.answer(
        "📸 Iltimos to'lov chekini <b>rasm</b> yoki <b>fayl</b> sifatida yuboring."
    )


# ============ 💎 /premium buyrug'i (status ko'rish) ============

from aiogram.filters import Command


@router.message(Command("premium"))
async def cmd_premium_status(message: Message, config: Config) -> None:
    """Foydalanuvchi o'z premium holatini va sotib olish ma'lumotlarini ko'radi."""
    if message.from_user is None:
        return
    is_prem = await models.is_premium(message.from_user.id)
    if is_prem:
        user = await models.get_user(message.from_user.id)
        until = (user or {}).get("premium_until", "")[:10] if user else ""
        await message.answer(
            f"💎 <b>Siz Premium foydalanuvchisiz!</b>\n\n"
            f"Faollik muddati: <b>{until}</b> gacha\n\n"
            f"Premium afzalliklari:\n"
            f"• Anketalarning lichkasiga to'g'ridan o'tish\n"
            f"• Anketangizda 💎 belgisi\n"
            f"• Maxsus broadcast'lar",
            reply_markup=reply.main_menu(),
        )
    else:
        await message.answer(
            _paywall_text(config),
            reply_markup=inline.premium_paywall_kb(),
        )

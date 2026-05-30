from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Qidirish"), KeyboardButton(text="👤 Profil")],
            [KeyboardButton(text="💌 Mosliklar"), KeyboardButton(text="❓ Yordam")],
        ],
        resize_keyboard=True,
    )


def gender_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="👨 Erkak"), KeyboardButton(text="👩 Ayol")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def looking_for_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨 Erkak"), KeyboardButton(text="👩 Ayol")],
            [KeyboardButton(text="🌈 Farqi yo'q")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def skip_kb(text: str = "⏭ O'tkazib yuborish") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=text)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )


def location_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Lokatsiya yuborish", request_location=True)],
            [KeyboardButton(text="⏭ O'tkazib yuborish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def search_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="❤️ Yoqdi"),
                KeyboardButton(text="👎 Yoqmadi"),
                KeyboardButton(text="🚫 Shikoyat"),
            ],
            [KeyboardButton(text="🏠 Asosiy menyu")],
        ],
        resize_keyboard=True,
    )


def chat_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔚 Suhbatni tugatish")]],
        resize_keyboard=True,
    )


def confirm_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Ha, to'g'ri"), KeyboardButton(text="🔄 Qayta to'ldirish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


remove = ReplyKeyboardRemove()

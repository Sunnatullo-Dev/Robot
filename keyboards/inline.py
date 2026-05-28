from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from data.regions import REGIONS


def regions_kb(prefix: str) -> InlineKeyboardMarkup:
    """Barcha viloyatlarni 2 ustunda ko'rsatadi. prefix: 'reg' yoki 'edit'."""
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for i, r in enumerate(REGIONS):
        row.append(InlineKeyboardButton(text=r["name"], callback_data=f"{prefix}:r:{i}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def districts_kb(prefix: str, region_idx: int) -> InlineKeyboardMarkup:
    """Tanlangan viloyatdagi tuman/shaharlar + 'Orqaga' tugmasi."""
    region = REGIONS[region_idx]
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for i, d in enumerate(region["districts"]):
        row.append(InlineKeyboardButton(text=d, callback_data=f"{prefix}:c:{region_idx}:{i}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="« Viloyatlarga qaytish", callback_data=f"{prefix}:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Ism", callback_data="edit:name"),
             InlineKeyboardButton(text="🎂 Yosh", callback_data="edit:age")],
            [InlineKeyboardButton(text="🏙 Shahar", callback_data="edit:city"),
             InlineKeyboardButton(text="💬 Bio", callback_data="edit:bio")],
            [InlineKeyboardButton(text="📷 Rasm", callback_data="edit:photo"),
             InlineKeyboardButton(text="💕 Kimni qidirish", callback_data="edit:looking_for")],
            [InlineKeyboardButton(text="🗑 Anketani o'chirish", callback_data="edit:delete")],
        ]
    )


def matches_kb(matches: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for m in matches[:20]:
        title = f"💕 {m['name']}, {m['age']}"
        rows.append([
            InlineKeyboardButton(text=title, callback_data=f"match_view:{m['user_id']}"),
        ])
    if not rows:
        rows.append([InlineKeyboardButton(text="—", callback_data="noop")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def match_actions_kb(partner_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Suhbat boshlash", callback_data=f"chat_start:{partner_id}")],
            [InlineKeyboardButton(text="🚫 Shikoyat qilish", callback_data=f"report:{partner_id}")],
            [InlineKeyboardButton(text="« Orqaga", callback_data="matches_back")],
        ]
    )


def report_reasons_kb(partner_id: int) -> InlineKeyboardMarkup:
    reasons = [
        ("Spam / reklama", "spam"),
        ("Haqoratlash", "abuse"),
        ("Soxta anketa", "fake"),
        ("18+ kontent", "nsfw"),
        ("Boshqa", "other"),
    ]
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"reportr:{partner_id}:{code}")]
        for label, code in reasons
    ]
    rows.append([InlineKeyboardButton(text="« Bekor qilish", callback_data="report_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Statistika", callback_data="adm:stats")],
            [InlineKeyboardButton(text="📢 Broadcast", callback_data="adm:broadcast")],
            [InlineKeyboardButton(text="🚫 Ban", callback_data="adm:ban"),
             InlineKeyboardButton(text="✅ Unban", callback_data="adm:unban")],
        ]
    )

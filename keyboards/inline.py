from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from data.regions import REGIONS


def like_response_kb(liker_id: int) -> InlineKeyboardMarkup:
    """Like notification ostidagi tugmalar (recipient uchun)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Suhbat boshlash", callback_data=f"likeresp:chat:{liker_id}")],
            [InlineKeyboardButton(text="👎 Yoqmadi", callback_data=f"likeresp:no:{liker_id}")],
        ]
    )


def chat_start_only_kb(partner_id: int) -> InlineKeyboardMarkup:
    """Bitta tugma: 💬 Suhbat boshlash."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Suhbat boshlash", callback_data=f"chat_start:{partner_id}")],
        ]
    )


def candidate_dm_kb(partner_id: int) -> InlineKeyboardMarkup:
    """Qidiruvdagi anketa tagidagi tugma — Lichkaga o'tish (premium)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💌 Lichkaga o'tish", callback_data=f"dm:{partner_id}")],
        ]
    )


def premium_paywall_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 To'lov chekini yuborish", callback_data="prem:paid")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="prem:cancel")],
        ]
    )


def premium_approval_kb(user_id: int, days: int = 30) -> InlineKeyboardMarkup:
    """Adminga keladigan chek ostiga: bir tugma bilan tasdiqlash yoki rad etish."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"✅ Tasdiqlash ({days} kun)",
                callback_data=f"premapprove:{user_id}:{days}",
            )],
            [InlineKeyboardButton(
                text="❌ Rad etish",
                callback_data=f"premreject:{user_id}",
            )],
            [InlineKeyboardButton(
                text="⚙️ Boshqa muddat...",
                callback_data=f"premcustom:{user_id}",
            )],
        ]
    )


def open_chat_kb(username: str | None, user_id: int) -> InlineKeyboardMarkup:
    """Telegram'da odamning lichkasini ochish tugmasi."""
    if username:
        url = f"https://t.me/{username}"
        text = f"➡️ @{username}"
    else:
        url = f"tg://user?id={user_id}"
        text = "➡️ Chatga o'tish"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, url=url)]]
    )


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
             InlineKeyboardButton(text="📍 Lokatsiya", callback_data="edit:location")],
            [InlineKeyboardButton(text="💬 Bio", callback_data="edit:bio"),
             InlineKeyboardButton(text="📷 Rasm", callback_data="edit:photo")],
            [InlineKeyboardButton(text="🎤 Ovoz", callback_data="edit:voice")],
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
    """Admin V2 — to'liq boshqaruv markazi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Dashboard", callback_data="adm:dashboard")],
            [InlineKeyboardButton(text="🔍 Monitoring", callback_data="mon:menu")],
            [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="adm:users"),
             InlineKeyboardButton(text="⚠️ Shikoyatlar", callback_data="adm:reports")],
            [InlineKeyboardButton(text="📢 Broadcast", callback_data="adm:broadcast_menu"),
             InlineKeyboardButton(text="💎 Premium narx", callback_data="adm:premium_set")],
            [InlineKeyboardButton(text="🤖 Sozlamalar", callback_data="adm:settings"),
             InlineKeyboardButton(text="🧪 Test tizimi", callback_data="adm:devtools")],
            [InlineKeyboardButton(text="📂 Loglar", callback_data="adm:logs"),
             InlineKeyboardButton(text="⚙️ Server holati", callback_data="adm:server")],
        ]
    )


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="« Admin panelga qaytish", callback_data="adm:back")],
        ]
    )


def admin_users_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Foydalanuvchi qidirish", callback_data="adm:search")],
            [InlineKeyboardButton(text="🚫 Ban (ID bo'yicha)", callback_data="adm:ban"),
             InlineKeyboardButton(text="✅ Unban", callback_data="adm:unban")],
            [InlineKeyboardButton(text="« Orqaga", callback_data="adm:back")],
        ]
    )


def admin_user_card_kb(user_id: int, is_banned: bool, is_shadow: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if is_banned:
        rows.append([InlineKeyboardButton(text="✅ Unban", callback_data=f"adm:uact:unban:{user_id}")])
    else:
        rows.append([InlineKeyboardButton(text="🚫 Ban", callback_data=f"adm:uact:ban:{user_id}")])

    if is_shadow:
        rows.append([InlineKeyboardButton(text="👁 Shadowban olib tashlash", callback_data=f"adm:uact:unshadow:{user_id}")])
    else:
        rows.append([InlineKeyboardButton(text="👁 Shadowban", callback_data=f"adm:uact:shadow:{user_id}")])

    rows.append([InlineKeyboardButton(text="📜 Shikoyatlar tarixi", callback_data=f"adm:uact:reports:{user_id}")])
    rows.append([InlineKeyboardButton(text="🗑 Anketani butunlay o'chirish", callback_data=f"adm:uact:delete:{user_id}")])
    rows.append([InlineKeyboardButton(text="« Orqaga", callback_data="adm:users")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_broadcast_filter_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Hammasiga", callback_data="adm:bcast:all")],
            [InlineKeyboardButton(text="👨 Faqat erkaklar", callback_data="adm:bcast:male"),
             InlineKeyboardButton(text="👩 Faqat ayollar", callback_data="adm:bcast:female")],
            [InlineKeyboardButton(text="🟢 Faqat faollar (7 kun)", callback_data="adm:bcast:active")],
            [InlineKeyboardButton(text="🏙 Viloyat bo'yicha", callback_data="adm:bcast:region")],
            [InlineKeyboardButton(text="« Orqaga", callback_data="adm:back")],
        ]
    )


def admin_reports_kb(reports: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for r in reports[:15]:
        name = r.get("name") or f"ID:{r['to_user_id']}"
        label = f"⚠️ {name} ({r['count']} ta)"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"adm:rpt:{r['to_user_id']}")])
    rows.append([InlineKeyboardButton(text="« Orqaga", callback_data="adm:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_report_actions_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Foydalanuvchini ban", callback_data=f"adm:uact:ban:{user_id}"),
             InlineKeyboardButton(text="👁 Shadowban", callback_data=f"adm:uact:shadow:{user_id}")],
            [InlineKeyboardButton(text="✅ Shikoyatlarni yopish", callback_data=f"adm:rptr:{user_id}")],
            [InlineKeyboardButton(text="« Orqaga", callback_data="adm:reports")],
        ]
    )


def admin_settings_kb(settings: dict[str, str]) -> InlineKeyboardMarkup:
    def b(name: str, key: str) -> str:
        return f"{'✅' if settings.get(key) == '1' else '❌'} {name}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("Ro'yxatdan o'tish", "registration_enabled"),
                                  callback_data="adm:set_toggle:registration_enabled")],
            [InlineKeyboardButton(text=b("Avto-ban", "auto_ban_enabled"),
                                  callback_data="adm:set_toggle:auto_ban_enabled")],
            [InlineKeyboardButton(
                text=f"⚙️ Avto-ban chegarasi: {settings.get('auto_ban_threshold', '3')}",
                callback_data="adm:set_edit:auto_ban_threshold",
            )],
            [InlineKeyboardButton(
                text=f"🎂 Minimal yosh: {settings.get('min_age', '14')}",
                callback_data="adm:set_edit:min_age",
            )],
            [InlineKeyboardButton(
                text=f"❤️ Kunlik like cheklovi: {settings.get('daily_likes_limit', '0') or 'cheksiz'}",
                callback_data="adm:set_edit:daily_likes_limit",
            )],
            [InlineKeyboardButton(text="« Orqaga", callback_data="adm:back")],
        ]
    )


def admin_premium_settings_kb(price: str, card: str, days: str, holder: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"💰 Narxi: {price}",
                callback_data="adm:set_edit:premium_price",
            )],
            [InlineKeyboardButton(
                text=f"💳 Karta: {card}",
                callback_data="adm:set_edit:premium_card",
            )],
            [InlineKeyboardButton(
                text=f"👤 Karta egasi: {holder or '(yo''q)'}",
                callback_data="adm:set_edit:premium_card_holder",
            )],
            [InlineKeyboardButton(
                text=f"📅 Premium muddati: {days} kun",
                callback_data="adm:set_edit:premium_days",
            )],
            [InlineKeyboardButton(text="« Orqaga", callback_data="adm:back")],
        ]
    )


def admin_devtools_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧪 Test anketalar qo'shish", callback_data="adm:dev:seed"),
             InlineKeyboardButton(text="🗑 Testlarni o'chirish", callback_data="adm:dev:unseed")],
            [InlineKeyboardButton(text="💾 DB Backup", callback_data="adm:dev:backup")],
            [InlineKeyboardButton(text="📤 CSV Export", callback_data="adm:dev:csv")],
            [InlineKeyboardButton(text="« Orqaga", callback_data="adm:back")],
        ]
    )

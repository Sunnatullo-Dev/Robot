"""Content filter — chat xabarlarida taqiqlangan kontentni aniqlash.

Regex asosida tezkor — har bir relay'dan oldin ishlatilinadi. Yengil va
xotirada o'qiladi (kompilyatsiya bir marta).

Detection turlari:
- USERNAME_DETECTED — @username (Telegram)
- LINK_DETECTED — t.me, telegram.me, wa.me, instagram, facebook, http(s)
- PHONE_DETECTED — telefon raqami (+998, +1, ...)
- EMAIL_DETECTED — email manzili
"""
from __future__ import annotations

import re
from typing import Optional

from database.violations import ViolationReason


# Tezkor regex'lar — bir marta kompilyatsiya qilinadi
# DIQQAT: email pattern username pattern'dan oldin tekshirilishi kerak
# (chunki "ali@gmail.com" dagi "@gmail" username sifatida noto'g'ri match bo'lishi mumkin)
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Email — birinchi tekshiriladi (username collision'dan saqlanish uchun)
    (ViolationReason.EMAIL_DETECTED, re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )),

    # Telegram usernames (5-32 belgi, harf bilan boshlanadi)
    # Negative lookbehind: oldidan harf bo'lmaslik kerak (email qismi emas)
    (ViolationReason.USERNAME_DETECTED, re.compile(r"(?<![A-Za-z0-9_.])@[a-zA-Z][a-zA-Z0-9_]{4,31}\b")),

    # Linklar
    (ViolationReason.LINK_DETECTED, re.compile(r"\bt\.me/[a-zA-Z0-9_+\-/]+", re.IGNORECASE)),
    (ViolationReason.LINK_DETECTED, re.compile(r"\btelegram\.me/[a-zA-Z0-9_+\-/]+", re.IGNORECASE)),
    (ViolationReason.LINK_DETECTED, re.compile(r"\bwa\.me/[0-9]+", re.IGNORECASE)),
    (ViolationReason.LINK_DETECTED, re.compile(r"\bwhatsapp\.com/[a-zA-Z0-9_+\-/]+", re.IGNORECASE)),
    (ViolationReason.LINK_DETECTED, re.compile(r"\binstagram\.com/[a-zA-Z0-9._+\-/]+", re.IGNORECASE)),
    (ViolationReason.LINK_DETECTED, re.compile(r"\bfacebook\.com/[a-zA-Z0-9._+\-/]+", re.IGNORECASE)),
    (ViolationReason.LINK_DETECTED, re.compile(r"\bfb\.com/[a-zA-Z0-9._+\-/]+", re.IGNORECASE)),
    (ViolationReason.LINK_DETECTED, re.compile(r"\btiktok\.com/[a-zA-Z0-9._@+\-/]+", re.IGNORECASE)),
    (ViolationReason.LINK_DETECTED, re.compile(r"\bhttps?://\S+", re.IGNORECASE)),

    # Telefon raqamlari
    # +998 90 123 45 67, +998901234567, 998901234567
    (ViolationReason.PHONE_DETECTED, re.compile(r"\+998[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b")),
    (ViolationReason.PHONE_DETECTED, re.compile(r"\b998\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2}\b")),
    # +1, +44 va boshqa international (10-15 raqam)
    (ViolationReason.PHONE_DETECTED, re.compile(r"\+\d{10,15}\b")),
    # Sof 9-13 raqamli ketma-ketlik (telefon shubha)
    (ViolationReason.PHONE_DETECTED, re.compile(r"\b\d{9,13}\b")),
]


# False-positive'larni kamaytirish uchun chetlatish — agar matn juda
# qisqa bo'lsa va faqat raqamlardan iborat bo'lsa, telefon deb hisoblanmaydi
# (foydalanuvchi yoshini aytayotgan bo'lishi mumkin)
def _is_safe_short_number(text: str) -> bool:
    stripped = text.strip()
    return stripped.isdigit() and len(stripped) <= 4


def detect_violation(text: Optional[str]) -> Optional[tuple[str, str]]:
    """Matnda taqiqlangan kontentni topish.

    Returns:
        (reason, matched_substring) yoki None — agar hech narsa topilmasa.
    """
    if not text:
        return None

    # Qisqa raqamlarni o'tkazib yuborish (yosh, sana va h.k.)
    if _is_safe_short_number(text):
        return None

    for reason, pattern in _PATTERNS:
        match = pattern.search(text)
        if match:
            return reason, match.group()

    return None

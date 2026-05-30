"""Moderation service — qoidabuzarlik aniqlanganda javob qoidalari.

Eskalatsiya:
- 1-buzilish → Ogohlantirish (warn)
- 2-buzilish → 24 soat mute
- 3+ buzilish → Doimiy ban

Bu modul fakat business logic — DB chaqiriqlari va xabar yuborish handler'da.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from database import alerts, models
from database.violations import (
    REASON_LABELS as VIOLATION_REASON_LABELS,
    add_violation,
    count_violations,
)

# Eskalatsiya chegaralari
WARN_AT = 1   # 1-buzilishdan boshlab ogohlantirish
MUTE_AT = 2   # 2-buzilishda mute
BAN_AT = 3    # 3-buzilishda ban
MUTE_HOURS = 24

# Mavjud alert reason'larga moderation reason'larini ham qo'shamiz
class ModerationReason:
    USERNAME_DETECTED = "USERNAME_DETECTED"
    PHONE_DETECTED = "PHONE_DETECTED"
    LINK_DETECTED = "LINK_DETECTED"
    EMAIL_DETECTED = "EMAIL_DETECTED"
    SPAM_DETECTED = "SPAM_DETECTED"


ActionType = Literal["warn", "mute", "ban"]


@dataclass(frozen=True)
class ModerationResult:
    action: ActionType
    violation_count: int
    reason: str
    reason_label: str


async def handle_violation(
    user_id: int, reason: str, message_text: str = "",
) -> ModerationResult:
    """Yangi qoidabuzarlikni qayd qilish va eskalatsiyani aniqlash.

    Returns: ModerationResult — qaysi amal qilinganligini ko'rsatadi.
    Handler bunga asoslanib mos xabar yuboradi.
    """
    # 1. Violations jadvaliga yozish
    await add_violation(user_id, reason, message_text)

    # 2. Jami buzilish soni
    count = await count_violations(user_id)
    reason_label = VIOLATION_REASON_LABELS.get(reason, reason)

    # 3. Alert ham yaratamiz (admin queue'sida ko'rinishi uchun)
    try:
        await alerts.create_alert(
            user_id, reason,
            details=f"#{count} buzilish: {message_text[:100]}",
        )
    except Exception:  # noqa: BLE001
        pass

    # 4. Eskalatsiya — yuqori chegaradan past chegaraga tartibda tekshirish
    if count >= BAN_AT:
        await models.set_banned(user_id, True)
        return ModerationResult("ban", count, reason, reason_label)

    if count >= MUTE_AT:
        await models.set_muted(user_id, MUTE_HOURS)
        return ModerationResult("mute", count, reason, reason_label)

    return ModerationResult("warn", count, reason, reason_label)


def format_action_message(result: ModerationResult) -> str:
    """Foydalanuvchiga ko'rsatiladigan xabar."""
    if result.action == "ban":
        return (
            f"🚫 <b>Hisob bloklandi</b>\n\n"
            f"Siz {result.violation_count} marta qoidabuzarlik qildingiz "
            f"(oxirgisi: {result.reason_label}).\n\n"
            f"Hisobingiz doimiy bloklandi. Adminga murojaat qiling."
        )

    if result.action == "mute":
        return (
            f"🔇 <b>Vaqtinchalik cheklov</b>\n\n"
            f"Bu sizning #{result.violation_count} buzilishingiz: "
            f"<i>{result.reason_label}</i>\n\n"
            f"Endi <b>{MUTE_HOURS} soat</b> chat yoza olmaysiz.\n\n"
            f"Yana 1 marta qoidani buzsangiz — doimiy bloklanish."
        )

    return (
        f"⚠️ <b>Ogohlantirish</b>\n\n"
        f"Sizning xabaringiz qoidabuzarlik aniqlandi: "
        f"<i>{result.reason_label}</i>\n\n"
        f"<b>Bot ichida quyidagilar taqiqlangan:</b>\n"
        f"• Telegram username (@...) yuborish\n"
        f"• Telefon raqami yuborish\n"
        f"• Tashqi havola (t.me, instagram, va h.k.) yuborish\n"
        f"• Email manzili yuborish\n\n"
        f"⚠️ <b>{2 - result.violation_count} ta ogohlantirishdan keyin "
        f"{MUTE_HOURS} soat mute, undan keyin doimiy ban.</b>"
    )

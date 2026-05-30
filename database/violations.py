"""Violations CRUD — chat moderation system uchun.

Foydalanuvchining qoidabuzarliklari (filter trigger, username/phone/link
yuborish va h.k.) shu yerga yoziladi. Eskalatsiya soni asosida warn → mute → ban.
"""
from __future__ import annotations

from typing import Any, Optional

import aiosqlite

from .db import get_db_path


class ViolationReason:
    """Qoidabuzarlik sabablari (constants)."""

    USERNAME_DETECTED = "USERNAME_DETECTED"
    PHONE_DETECTED = "PHONE_DETECTED"
    LINK_DETECTED = "LINK_DETECTED"
    EMAIL_DETECTED = "EMAIL_DETECTED"
    SPAM_DETECTED = "SPAM_DETECTED"
    PROFANITY_DETECTED = "PROFANITY_DETECTED"


REASON_LABELS: dict[str, str] = {
    ViolationReason.USERNAME_DETECTED: "Telegram username yuborildi",
    ViolationReason.PHONE_DETECTED: "Telefon raqami yuborildi",
    ViolationReason.LINK_DETECTED: "Tashqi havola yuborildi",
    ViolationReason.EMAIL_DETECTED: "Email yuborildi",
    ViolationReason.SPAM_DETECTED: "Spam aniqlandi",
    ViolationReason.PROFANITY_DETECTED: "Haqorat aniqlandi",
}


async def add_violation(
    user_id: int, reason: str, message_text: Optional[str] = None,
) -> int:
    """Yangi qoidabuzarlik yozish. Returns: violation ID."""
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            "INSERT INTO violations (user_id, reason, message_text) VALUES (?, ?, ?)",
            (user_id, reason, (message_text or "")[:500]),
        )
        await db.commit()
        return cur.lastrowid or 0


async def count_violations(user_id: int) -> int:
    """Foydalanuvchining jami qoidabuzarliklar soni."""
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM violations WHERE user_id = ?", (user_id,),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def get_user_violations(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    """Foydalanuvchining oxirgi N ta qoidabuzarliklari (admin uchun)."""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, user_id, reason, message_text, created_at
            FROM violations
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def reset_user_violations(user_id: int) -> int:
    """Foydalanuvchining barcha qoidabuzarliklarini o'chirish (admin amnistia).
    Returns: o'chirilgan qatorlar soni.
    """
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            "DELETE FROM violations WHERE user_id = ?", (user_id,),
        )
        await db.commit()
        return cur.rowcount or 0

"""Alerts CRUD — shubhali foydalanuvchilarni avtomatik aniqlash."""
from __future__ import annotations

from typing import Any, Optional

import aiosqlite

from .db import get_db_path


class AlertReason:
    """Alert sabablari (string constants)."""

    TOO_MANY_LIKES = "TOO_MANY_LIKES"
    TOO_MANY_REPORTS = "TOO_MANY_REPORTS"
    TOO_MANY_PROFILE_CHANGES = "TOO_MANY_PROFILE_CHANGES"
    SUSPICIOUS_PATTERN = "SUSPICIOUS_PATTERN"


class AlertStatus:
    """Alert holatlari."""

    PENDING = "pending"
    VIEWED = "viewed"
    RESOLVED = "resolved"


REASON_LABELS: dict[str, str] = {
    AlertReason.TOO_MANY_LIKES: "Juda ko'p like (5 daq)",
    AlertReason.TOO_MANY_REPORTS: "Ko'p shikoyat (5+)",
    AlertReason.TOO_MANY_PROFILE_CHANGES: "Profil tez-tez o'zgartirilgan",
    AlertReason.SUSPICIOUS_PATTERN: "Shubhali xatti-harakat",
}


async def create_alert(
    user_id: int, reason: str, details: str = "",
) -> Optional[int]:
    """Yangi alert yaratish.

    Agar shu user uchun shu reason bilan PENDING alert mavjud bo'lsa,
    yangi alert yaratilmaydi (dublikatdan saqlanish). Returns: alert ID.
    """
    async with aiosqlite.connect(get_db_path()) as db:
        # Faol pending alertni tekshirish
        async with db.execute(
            """
            SELECT id FROM alerts
            WHERE user_id = ? AND reason = ? AND status = 'pending'
            LIMIT 1
            """,
            (user_id, reason),
        ) as cur:
            existing = await cur.fetchone()
        if existing:
            return existing[0]

        cur = await db.execute(
            "INSERT INTO alerts (user_id, reason, details) VALUES (?, ?, ?)",
            (user_id, reason, details),
        )
        await db.commit()
        return cur.lastrowid


async def get_pending_alerts(limit: int = 20) -> list[dict[str, Any]]:
    """PENDING holatdagi alertlar, eng yangi birinchi (admin queue)."""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT
                a.id, a.user_id, a.reason, a.status, a.details, a.created_at,
                u.name, u.username, u.is_banned
            FROM alerts a
            LEFT JOIN users u ON u.user_id = a.user_id
            WHERE a.status = 'pending'
            ORDER BY a.id DESC
            LIMIT ?
            """,
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_alert(alert_id: int) -> Optional[dict[str, Any]]:
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT
                a.*, u.name, u.username, u.is_banned, u.is_shadow_banned
            FROM alerts a
            LEFT JOIN users u ON u.user_id = a.user_id
            WHERE a.id = ?
            """,
            (alert_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_status(alert_id: int, status: str) -> None:
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "UPDATE alerts SET status = ? WHERE id = ?", (status, alert_id),
        )
        await db.commit()


async def count_pending() -> int:
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM alerts WHERE status = 'pending'"
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

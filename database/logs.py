"""Event logs CRUD.

50k+ foydalanuvchi uchun mo'ljallangan: barcha querylarda LIMIT, har bir
ko'p qo'llaniladigan ustun uchun composite index, SELECT * dan qochish.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import aiosqlite

from .db import get_db_path

logger = logging.getLogger(__name__)


class EventType:
    """Mavjud event tiplari (string constants)."""

    USER_REGISTER = "USER_REGISTER"
    PROFILE_UPDATED = "PROFILE_UPDATED"
    PROFILE_DELETED = "PROFILE_DELETED"
    LIKE_SENT = "LIKE_SENT"
    DISLIKE_SENT = "DISLIKE_SENT"
    MATCH_CREATED = "MATCH_CREATED"
    CHAT_STARTED = "CHAT_STARTED"
    CHAT_ENDED = "CHAT_ENDED"
    REPORT_CREATED = "REPORT_CREATED"
    USER_BANNED = "USER_BANNED"
    USER_UNBANNED = "USER_UNBANNED"
    USER_SHADOW_BANNED = "USER_SHADOW_BANNED"
    PREMIUM_GRANTED = "PREMIUM_GRANTED"
    PREMIUM_REVOKED = "PREMIUM_REVOKED"
    VERIFIED = "VERIFIED"


# Foydalanuvchiga tushunarli matnlar (timeline ko'rsatish uchun)
EVENT_LABELS: dict[str, str] = {
    EventType.USER_REGISTER: "📝 Ro'yxatdan o'tdi",
    EventType.PROFILE_UPDATED: "✏️ Profilni yangiladi",
    EventType.PROFILE_DELETED: "🗑 Profilni o'chirdi",
    EventType.LIKE_SENT: "❤️ Like bosdi",
    EventType.DISLIKE_SENT: "👎 Dislike",
    EventType.MATCH_CREATED: "💞 Match",
    EventType.CHAT_STARTED: "💬 Suhbat boshladi",
    EventType.CHAT_ENDED: "🔚 Suhbat tugatdi",
    EventType.REPORT_CREATED: "🚫 Shikoyat berdi",
    EventType.USER_BANNED: "🚫 Bloklandi",
    EventType.USER_UNBANNED: "✅ Blokdan chiqarildi",
    EventType.USER_SHADOW_BANNED: "👁 Shadowban",
    EventType.PREMIUM_GRANTED: "💎 Premium berildi",
    EventType.PREMIUM_REVOKED: "💎 Premium tugadi",
    EventType.VERIFIED: "✅ Tasdiqlandi",
}


async def log_event(
    user_id: int,
    event_type: str,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Eventni `logs` jadvaliga yozish.

    Args:
        user_id: Telegram foydalanuvchi ID
        event_type: EventType class konstantalaridan biri
        metadata: JSON-serializable qo'shimcha ma'lumotlar (ixtiyoriy)
    """
    metadata_str: Optional[str] = None
    if metadata is not None:
        try:
            metadata_str = json.dumps(metadata, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as e:
            logger.warning("Failed to serialize metadata for %s: %s", event_type, e)

    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "INSERT INTO logs (user_id, event_type, metadata) VALUES (?, ?, ?)",
            (user_id, event_type, metadata_str),
        )
        await db.commit()


async def get_user_timeline(
    user_id: int, limit: int = 50, offset: int = 0,
) -> list[dict[str, Any]]:
    """Foydalanuvchining oxirgi N ta eventini qaytarish (pagination uchun)."""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, user_id, event_type, metadata, created_at
            FROM logs
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        ) as cur:
            rows = await cur.fetchall()

    results: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        meta = d.get("metadata")
        if meta:
            try:
                d["metadata"] = json.loads(meta)
            except (json.JSONDecodeError, TypeError):
                d["metadata"] = None
        results.append(d)
    return results


async def count_user_events(user_id: int) -> int:
    """Foydalanuvchi uchun jami event soni — pagination uchun."""
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM logs WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def count_events_in_window(
    user_id: int, event_type: str, minutes: int,
) -> int:
    """N daqiqada ushbu foydalanuvchining qilgan event soni (alerts uchun)."""
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute(
            """
            SELECT COUNT(*) FROM logs
            WHERE user_id = ?
              AND event_type = ?
              AND created_at >= datetime('now', ?)
            """,
            (user_id, event_type, f"-{minutes} minutes"),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def count_events_total(user_id: int, event_type: str) -> int:
    """Foydalanuvchi uchun ushbu turdagi eventlarning jami soni."""
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM logs WHERE user_id = ? AND event_type = ?",
            (user_id, event_type),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def get_event_aggregates(since_minutes: int = 1440) -> dict[str, int]:
    """Real-time dashboard uchun event'larning agregatsiyasi (bitta query).

    50k+ foydalanuvchi uchun: bitta SQL, indexdan foydalanish.
    """
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute(
            """
            SELECT event_type, COUNT(*) as cnt
            FROM logs
            WHERE created_at >= datetime('now', ?)
            GROUP BY event_type
            """,
            (f"-{since_minutes} minutes",),
        ) as cur:
            rows = await cur.fetchall()
            return {r[0]: r[1] for r in rows}


async def cleanup_old_logs(days: int = 90) -> int:
    """N kundan eski loglarni o'chirish (disk maydoni iqtisod uchun).

    Returns: o'chirilgan qatorlar soni.
    """
    async with aiosqlite.connect(get_db_path()) as db:
        cur = await db.execute(
            "DELETE FROM logs WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        await db.commit()
        return cur.rowcount or 0

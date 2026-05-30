"""Admin audit logs — har bir admin amalini yozish.

Bu modul `database/models.py`'dagi mavjud admin_logs funksiyalarining
clean wrapper'i. Yangi kodda mana shu importlaridan foydalaning.
"""
from __future__ import annotations

from typing import Any, Optional

import aiosqlite

from .db import get_db_path


# Standart admin amallari
class AdminAction:
    BAN = "ban"
    UNBAN = "unban"
    SHADOWBAN = "shadowban"
    UNSHADOWBAN = "unshadowban"
    DELETE_USER = "delete_user"
    BROADCAST = "broadcast"
    PREMIUM_APPROVE = "premium_approve"
    PREMIUM_REJECT = "premium_reject"
    PREMIUM_SET = "premium_set"
    VERIFY = "verify"
    ADD_ADMIN = "add_admin"
    REMOVE_ADMIN = "remove_admin"
    SEED = "seed"
    UNSEED = "unseed"
    DB_BACKUP = "db_backup"
    CSV_EXPORT = "csv_export"
    SETTING_CHANGE = "setting_change"


async def log_action(
    admin_id: int,
    action: str,
    target_id: Optional[int] = None,
    details: str = "",
) -> None:
    """Adminning amalini admin_logs jadvaliga yozish."""
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "INSERT INTO admin_logs (admin_id, action, target_id, details) "
            "VALUES (?, ?, ?, ?)",
            (admin_id, action, target_id, details),
        )
        await db.commit()


async def get_recent(limit: int = 30) -> list[dict[str, Any]]:
    """So'nggi admin amallari ro'yxati."""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, admin_id, action, target_id, details, created_at
            FROM admin_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_actions_on_user(user_id: int, limit: int = 30) -> list[dict[str, Any]]:
    """Ushbu foydalanuvchi ustida bajarilgan barcha admin amallari."""
    async with aiosqlite.connect(get_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT id, admin_id, action, target_id, details, created_at
            FROM admin_logs
            WHERE target_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

from typing import Any, Optional

import aiosqlite

from .db import get_db_path


def _conn() -> aiosqlite.Connection:
    return aiosqlite.connect(get_db_path())


# ============ USERS ============

async def get_user(user_id: int) -> Optional[dict[str, Any]]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_or_update_user(user_id: int, username: Optional[str]) -> None:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT INTO users (user_id, username) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                last_seen = CURRENT_TIMESTAMP
            """,
            (user_id, username),
        )
        await db.commit()


async def save_profile(
    user_id: int,
    name: str,
    age: int,
    gender: str,
    looking_for: str,
    city: str,
    bio: str,
    photo_id: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> None:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            UPDATE users SET
                name = ?, age = ?, gender = ?, looking_for = ?,
                city = ?, bio = ?, photo_id = ?,
                latitude = ?, longitude = ?, is_active = 1
            WHERE user_id = ?
            """,
            (name, age, gender, looking_for, city, bio, photo_id,
             latitude, longitude, user_id),
        )
        await db.commit()


async def update_location(user_id: int, lat: Optional[float], lon: Optional[float]) -> None:
    async with _conn() as db:
        await db.execute(
            "UPDATE users SET latitude = ?, longitude = ? WHERE user_id = ?",
            (lat, lon, user_id),
        )
        await db.commit()


async def update_field(user_id: int, field: str, value: Any) -> None:
    allowed = {"name", "age", "city", "bio", "photo_id", "looking_for", "is_active"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' o'zgartirib bo'lmaydi")
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        await db.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()


async def set_banned(user_id: int, banned: bool) -> None:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            "UPDATE users SET is_banned = ?, is_active = ? WHERE user_id = ?",
            (1 if banned else 0, 0 if banned else 1, user_id),
        )
        await db.commit()


async def is_banned(user_id: int) -> bool:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return bool(row and row[0])


# ============ SEARCH / FEED ============

async def get_next_candidate(user_id: int) -> Optional[dict[str, Any]]:
    """Mos keladigan anketani qaytaradi. Agar foydalanuvchining lokatsiyasi
    bo'lsa, eng yaqindagi (lekin shu paytgacha ko'rilmagan) odamni qaytaradi.
    Aks holda tasodifiy.
    """
    from utils.helpers import haversine_km

    user = await get_user(user_id)
    if not user or not user.get("gender") or not user.get("looking_for"):
        return None

    gender_filter = ""
    params: list[Any] = [user_id]
    if user["looking_for"] != "A":
        gender_filter = "AND u.gender = ?"
        params.append(user["looking_for"])

    looking_back = "AND (u.looking_for = ? OR u.looking_for = 'A')"
    params.append(user["gender"])
    params.append(user_id)

    has_my_loc = user.get("latitude") is not None and user.get("longitude") is not None

    if has_my_loc:
        # Lokatsiyasi bor barcha kandidatlarni olamiz, Python da masofa bo'yicha saralaymiz
        sql = f"""
            SELECT u.* FROM users u
            WHERE u.user_id != ?
              AND u.is_active = 1
              AND u.is_banned = 0
              AND u.photo_id IS NOT NULL
              {gender_filter}
              {looking_back}
              AND u.user_id NOT IN (
                  SELECT to_user_id FROM likes WHERE from_user_id = ?
              )
              AND u.latitude IS NOT NULL
              AND u.longitude IS NOT NULL
            LIMIT 200
        """
        async with _conn() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cur:
                rows = await cur.fetchall()

        if rows:
            cands = [dict(r) for r in rows]
            for c in cands:
                c["_distance"] = haversine_km(
                    user["latitude"], user["longitude"],
                    c["latitude"], c["longitude"],
                )
            cands.sort(key=lambda c: c["_distance"])
            return cands[0]

        # Lokatsiyali kandidat yo'q — tasodifiyga qaytamiz

    sql = f"""
        SELECT u.* FROM users u
        WHERE u.user_id != ?
          AND u.is_active = 1
          AND u.is_banned = 0
          AND u.photo_id IS NOT NULL
          {gender_filter}
          {looking_back}
          AND u.user_id NOT IN (
              SELECT to_user_id FROM likes WHERE from_user_id = ?
          )
        ORDER BY RANDOM()
        LIMIT 1
    """
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, params) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


# ============ LIKES / MATCHES ============

async def add_like(from_user: int, to_user: int, is_like: bool) -> bool:
    """Return True if this creates a mutual match."""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        await db.execute(
            """
            INSERT INTO likes (from_user_id, to_user_id, is_like) VALUES (?, ?, ?)
            ON CONFLICT(from_user_id, to_user_id) DO UPDATE SET is_like = excluded.is_like
            """,
            (from_user, to_user, 1 if is_like else 0),
        )
        await db.commit()

        if not is_like:
            return False

        async with db.execute(
            "SELECT is_like FROM likes WHERE from_user_id = ? AND to_user_id = ?",
            (to_user, from_user),
        ) as cur:
            row = await cur.fetchone()
            if not row or not row[0]:
                return False

        a, b = sorted([from_user, to_user])
        await db.execute(
            "INSERT OR IGNORE INTO matches (user1_id, user2_id) VALUES (?, ?)",
            (a, b),
        )
        await db.commit()
        return True


async def get_matches(user_id: int) -> list[dict[str, Any]]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT u.user_id, u.name, u.age, u.city, u.photo_id, u.username, m.id as match_id
            FROM matches m
            JOIN users u ON (
                u.user_id = CASE WHEN m.user1_id = ? THEN m.user2_id ELSE m.user1_id END
            )
            WHERE (m.user1_id = ? OR m.user2_id = ?)
              AND m.is_active = 1
              AND u.is_banned = 0
            ORDER BY m.created_at DESC
            """,
            (user_id, user_id, user_id),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_pending_likes(user_id: int) -> list[dict[str, Any]]:
    """Foydalanuvchini like bosgan, lekin u javob bermagan anketalar (premium funksiya uchun)."""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT u.user_id, u.name, u.age, u.city, u.photo_id, u.bio
            FROM likes l
            JOIN users u ON u.user_id = l.from_user_id
            WHERE l.to_user_id = ?
              AND l.is_like = 1
              AND u.is_banned = 0
              AND u.is_active = 1
              AND NOT EXISTS (
                  SELECT 1 FROM likes l2
                  WHERE l2.from_user_id = ? AND l2.to_user_id = l.from_user_id
              )
            ORDER BY l.created_at DESC
            LIMIT 20
            """,
            (user_id, user_id),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ============ ANONYMOUS CHAT ============

async def start_chat(user_id: int, partner_id: int, match_id: int) -> None:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("DELETE FROM active_chats WHERE user_id IN (?, ?)", (user_id, partner_id))
        await db.execute(
            "INSERT INTO active_chats (user_id, partner_id, match_id) VALUES (?, ?, ?), (?, ?, ?)",
            (user_id, partner_id, match_id, partner_id, user_id, match_id),
        )
        await db.commit()


async def stop_chat(user_id: int) -> Optional[int]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT partner_id FROM active_chats WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            partner = row[0] if row else None

        if partner:
            await db.execute(
                "DELETE FROM active_chats WHERE user_id IN (?, ?)", (user_id, partner)
            )
            await db.commit()
        return partner


async def get_chat_partner(user_id: int) -> Optional[int]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT partner_id FROM active_chats WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


# ============ REPORTS ============

async def add_report(from_user: int, to_user: int, reason: str) -> int:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "INSERT INTO reports (from_user_id, to_user_id, reason) VALUES (?, ?, ?)",
            (from_user, to_user, reason),
        )
        await db.commit()
        return cur.lastrowid or 0


async def reports_count(user_id: int) -> int:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT COUNT(*) FROM reports WHERE to_user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


# ============ ADMIN / STATS ============

async def stats() -> dict[str, int]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        result: dict[str, int] = {}
        queries = {
            "total_users": "SELECT COUNT(*) FROM users",
            "active_users": "SELECT COUNT(*) FROM users WHERE is_active = 1 AND is_banned = 0",
            "with_profile": "SELECT COUNT(*) FROM users WHERE photo_id IS NOT NULL",
            "banned_users": "SELECT COUNT(*) FROM users WHERE is_banned = 1",
            "total_matches": "SELECT COUNT(*) FROM matches",
            "total_likes": "SELECT COUNT(*) FROM likes WHERE is_like = 1",
            "total_reports": "SELECT COUNT(*) FROM reports",
        }
        for key, sql in queries.items():
            async with db.execute(sql) as cur:
                row = await cur.fetchone()
                result[key] = row[0] if row else 0
        return result


async def all_active_user_ids() -> list[int]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id FROM users WHERE is_banned = 0"
        ) as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]

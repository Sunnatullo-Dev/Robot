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


async def upsert_seed_user(
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
    """Test foydalanuvchi yaratish yoki yangilash (/seed buyrug'i uchun)."""
    async with _conn() as db:
        await db.execute(
            """
            INSERT INTO users (
                user_id, username, name, age, gender, looking_for,
                city, bio, photo_id, latitude, longitude, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name,
                age = excluded.age,
                gender = excluded.gender,
                looking_for = excluded.looking_for,
                city = excluded.city,
                bio = excluded.bio,
                photo_id = excluded.photo_id,
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                is_active = 1
            """,
            (user_id, f"test_{user_id}", name, age, gender, looking_for,
             city, bio, photo_id, latitude, longitude),
        )
        await db.commit()


async def delete_seed_users(base_id: int) -> int:
    """base_id dan boshlanadigan barcha test foydalanuvchilarni o'chiradi."""
    async with _conn() as db:
        cur = await db.execute(
            "DELETE FROM users WHERE user_id >= ?", (base_id,)
        )
        # Bog'liq ma'lumotlarni ham tozalash
        await db.execute(
            "DELETE FROM likes WHERE from_user_id >= ? OR to_user_id >= ?",
            (base_id, base_id),
        )
        await db.execute(
            "DELETE FROM matches WHERE user1_id >= ? OR user2_id >= ?",
            (base_id, base_id),
        )
        await db.commit()
        return cur.rowcount or 0


async def update_voice(user_id: int, voice_id: Optional[str]) -> None:
    async with _conn() as db:
        await db.execute(
            "UPDATE users SET voice_id = ? WHERE user_id = ?",
            (voice_id, user_id),
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


async def set_shadow_banned(user_id: int, shadow: bool) -> None:
    """Shadowban — foydalanuvchi botda hech narsa o'zgarmagandek ko'radi,
    lekin uning anketasi qidiruvda boshqalarga ko'rinmaydi."""
    async with _conn() as db:
        await db.execute(
            "UPDATE users SET is_shadow_banned = ? WHERE user_id = ?",
            (1 if shadow else 0, user_id),
        )
        await db.commit()


# ============ PREMIUM ============

async def set_premium(user_id: int, days: int) -> None:
    """days=0 → premium olib tashlanadi; >0 → shu kungacha premium beriladi."""
    async with _conn() as db:
        if days <= 0:
            await db.execute(
                "UPDATE users SET premium_until = NULL WHERE user_id = ?",
                (user_id,),
            )
        else:
            await db.execute(
                "UPDATE users SET premium_until = datetime('now', ?) "
                "WHERE user_id = ?",
                (f"+{days} days", user_id),
            )
        await db.commit()


async def is_premium(user_id: int) -> bool:
    async with _conn() as db:
        async with db.execute(
            "SELECT premium_until FROM users "
            "WHERE user_id = ? AND premium_until > CURRENT_TIMESTAMP",
            (user_id,),
        ) as cur:
            return await cur.fetchone() is not None


# ============ ROLE TIZIMI ============

VALID_ROLES = ("owner", "super_admin", "admin", "moderator", "support")


async def ensure_owners(owner_ids: list[int]) -> None:
    """`.env`'dagi ADMIN_IDS'larni 'owner' rolida ro'yxatga oladi (bir marta)."""
    if not owner_ids:
        return
    async with _conn() as db:
        for uid in owner_ids:
            await db.execute(
                """
                INSERT INTO admins (user_id, role, added_by) VALUES (?, 'owner', ?)
                ON CONFLICT(user_id) DO UPDATE SET role = 'owner'
                """,
                (uid, uid),
            )
        await db.commit()


async def add_admin_role(user_id: int, role: str, added_by: int) -> None:
    if role not in VALID_ROLES:
        raise ValueError(f"Noma'lum role: {role}")
    async with _conn() as db:
        await db.execute(
            """
            INSERT INTO admins (user_id, role, added_by) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET role = excluded.role
            """,
            (user_id, role, added_by),
        )
        await db.commit()


async def remove_admin_role(user_id: int) -> None:
    async with _conn() as db:
        await db.execute("DELETE FROM admins WHERE user_id = ? AND role != 'owner'", (user_id,))
        await db.commit()


async def get_admin_role(user_id: int) -> Optional[str]:
    async with _conn() as db:
        async with db.execute("SELECT role FROM admins WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def list_admins() -> list[dict[str, Any]]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT a.user_id, a.role, a.added_at, u.name, u.username
            FROM admins a
            LEFT JOIN users u ON u.user_id = a.user_id
            ORDER BY
                CASE a.role
                    WHEN 'owner' THEN 1
                    WHEN 'super_admin' THEN 2
                    WHEN 'admin' THEN 3
                    WHEN 'moderator' THEN 4
                    WHEN 'support' THEN 5
                END
            """
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def set_verified(user_id: int, verified: bool) -> None:
    async with _conn() as db:
        await db.execute(
            "UPDATE users SET is_verified = ? WHERE user_id = ?",
            (1 if verified else 0, user_id),
        )
        await db.commit()


async def get_premium_users(limit: int = 50) -> list[dict[str, Any]]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT user_id, name, username, premium_until
            FROM users
            WHERE premium_until IS NOT NULL AND premium_until > CURRENT_TIMESTAMP
            ORDER BY premium_until DESC
            LIMIT ?
            """,
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def hard_delete_user(user_id: int) -> None:
    """Foydalanuvchini va bog'liq ma'lumotlarini butunlay o'chirib tashlash."""
    async with _conn() as db:
        await db.execute("DELETE FROM active_chats WHERE user_id = ? OR partner_id = ?", (user_id, user_id))
        await db.execute("DELETE FROM likes WHERE from_user_id = ? OR to_user_id = ?", (user_id, user_id))
        await db.execute("DELETE FROM matches WHERE user1_id = ? OR user2_id = ?", (user_id, user_id))
        await db.execute("DELETE FROM reports WHERE from_user_id = ? OR to_user_id = ?", (user_id, user_id))
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()


# ============ USER SEARCH (ADMIN) ============

async def find_users(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Foydalanuvchini ID, username yoki ism bo'yicha qidirish."""
    query = query.strip()
    if not query:
        return []

    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        if query.isdigit():
            async with db.execute(
                "SELECT * FROM users WHERE user_id = ? LIMIT ?",
                (int(query), limit),
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

        like = f"%{query.lstrip('@')}%"
        async with db.execute(
            """
            SELECT * FROM users
            WHERE username LIKE ? OR name LIKE ?
            ORDER BY last_seen DESC
            LIMIT ?
            """,
            (like, like, limit),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ============ BOT SETTINGS ============

async def get_setting(key: str, default: str = "") -> str:
    async with _conn() as db:
        async with db.execute(
            "SELECT value FROM bot_settings WHERE key = ?", (key,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else default


async def set_setting(key: str, value: str) -> None:
    async with _conn() as db:
        await db.execute(
            """
            INSERT INTO bot_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        await db.commit()


async def get_all_settings() -> dict[str, str]:
    async with _conn() as db:
        async with db.execute("SELECT key, value FROM bot_settings") as cur:
            rows = await cur.fetchall()
            return {r[0]: r[1] for r in rows}


# ============ ADMIN LOGS ============

async def log_admin_action(
    admin_id: int, action: str, target_id: Optional[int] = None, details: str = ""
) -> None:
    async with _conn() as db:
        await db.execute(
            "INSERT INTO admin_logs (admin_id, action, target_id, details) VALUES (?, ?, ?, ?)",
            (admin_id, action, target_id, details),
        )
        await db.commit()


async def get_admin_logs(limit: int = 30) -> list[dict[str, Any]]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ============ REPORT QUEUE (ADMIN) ============

async def get_pending_reports(limit: int = 20) -> list[dict[str, Any]]:
    """Hali ko'rib chiqilmagan shikoyatlar, foydalanuvchi bo'yicha guruhlangan."""
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT
                r.to_user_id,
                u.name,
                u.username,
                COUNT(*) as count,
                MAX(r.created_at) as last_report
            FROM reports r
            LEFT JOIN users u ON u.user_id = r.to_user_id
            WHERE COALESCE(r.status, 'pending') = 'pending'
            GROUP BY r.to_user_id
            ORDER BY count DESC, last_report DESC
            LIMIT ?
            """,
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_user_reports(user_id: int) -> list[dict[str, Any]]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM reports
            WHERE to_user_id = ?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def resolve_reports(user_id: int) -> int:
    """Foydalanuvchiga oid barcha shikoyatlarni 'reviewed' qilish."""
    async with _conn() as db:
        cur = await db.execute(
            "UPDATE reports SET status = 'reviewed' WHERE to_user_id = ?", (user_id,)
        )
        await db.commit()
        return cur.rowcount or 0


# ============ FILTERED BROADCAST AUDIENCE ============

async def get_audience_ids(filter_type: str, value: str = "") -> list[int]:
    """
    filter_type:
      - 'all' — bloklanmagan barcha
      - 'male' — faqat erkaklar
      - 'female' — faqat ayollar
      - 'region' — value = viloyat nomi (LIKE qidiruv)
      - 'active' — so'nggi 7 kunda online bo'lgan
      - 'premium' — premium muddatli foydalanuvchilar
    """
    async with _conn() as db:
        if filter_type == "male":
            sql = "SELECT user_id FROM users WHERE is_banned = 0 AND gender = 'M'"
            params: tuple = ()
        elif filter_type == "female":
            sql = "SELECT user_id FROM users WHERE is_banned = 0 AND gender = 'F'"
            params = ()
        elif filter_type == "region":
            sql = "SELECT user_id FROM users WHERE is_banned = 0 AND city LIKE ?"
            params = (f"%{value}%",)
        elif filter_type == "active":
            sql = (
                "SELECT user_id FROM users "
                "WHERE is_banned = 0 AND last_seen >= datetime('now', '-7 days')"
            )
            params = ()
        elif filter_type == "premium":
            sql = (
                "SELECT user_id FROM users "
                "WHERE is_banned = 0 AND premium_until IS NOT NULL "
                "AND premium_until > CURRENT_TIMESTAMP"
            )
            params = ()
        else:
            sql = "SELECT user_id FROM users WHERE is_banned = 0"
            params = ()

        async with db.execute(sql, params) as cur:
            return [r[0] for r in await cur.fetchall()]


# ============ EXTENDED STATS ============

async def detailed_stats() -> dict[str, Any]:
    """Dashboard uchun batafsil real-time statistika."""
    async with _conn() as db:
        result: dict[str, Any] = {}
        queries = {
            "total_users": "SELECT COUNT(*) FROM users",
            "with_profile": "SELECT COUNT(*) FROM users WHERE photo_id IS NOT NULL",
            "active_users": "SELECT COUNT(*) FROM users WHERE is_active=1 AND is_banned=0",
            "banned_users": "SELECT COUNT(*) FROM users WHERE is_banned=1",
            "shadow_banned": "SELECT COUNT(*) FROM users WHERE is_shadow_banned=1",
            "males": "SELECT COUNT(*) FROM users WHERE gender='M'",
            "females": "SELECT COUNT(*) FROM users WHERE gender='F'",
            "online_24h": (
                "SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now','-1 day')"
            ),
            "online_7d": (
                "SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now','-7 days')"
            ),
            "new_today": (
                "SELECT COUNT(*) FROM users WHERE created_at >= date('now')"
            ),
            "new_7d": (
                "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now','-7 days')"
            ),
            "total_likes": "SELECT COUNT(*) FROM likes WHERE is_like=1",
            "likes_today": (
                "SELECT COUNT(*) FROM likes WHERE is_like=1 AND created_at >= date('now')"
            ),
            "total_matches": "SELECT COUNT(*) FROM matches",
            "matches_today": (
                "SELECT COUNT(*) FROM matches WHERE created_at >= date('now')"
            ),
            "active_chats": "SELECT COUNT(*)/2 FROM active_chats",
            "total_reports": "SELECT COUNT(*) FROM reports",
            "pending_reports": (
                "SELECT COUNT(*) FROM reports WHERE COALESCE(status,'pending') = 'pending'"
            ),
        }
        for key, sql in queries.items():
            async with db.execute(sql) as cur:
                row = await cur.fetchone()
                result[key] = row[0] if row else 0

        # Top 5 viloyat
        async with db.execute(
            """
            SELECT
                CASE WHEN INSTR(city, ',') > 0
                     THEN TRIM(SUBSTR(city, 1, INSTR(city, ',') - 1))
                     ELSE city
                END AS region,
                COUNT(*) AS cnt
            FROM users
            WHERE city IS NOT NULL AND city != ''
            GROUP BY region
            ORDER BY cnt DESC
            LIMIT 5
            """
        ) as cur:
            result["top_regions"] = [(r[0], r[1]) for r in await cur.fetchall()]

        return result


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
              AND COALESCE(u.is_shadow_banned, 0) = 0
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

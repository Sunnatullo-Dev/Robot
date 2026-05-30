import os

import aiosqlite

_DB_PATH: str = "tanishuv.db"


def get_db_path() -> str:
    return _DB_PATH


async def init_db(path: str) -> None:
    global _DB_PATH
    _DB_PATH = path

    parent = os.path.dirname(os.path.abspath(_DB_PATH))
    if parent:
        os.makedirs(parent, exist_ok=True)

    async with aiosqlite.connect(_DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id      INTEGER PRIMARY KEY,
                username     TEXT,
                name         TEXT,
                age          INTEGER,
                gender       TEXT CHECK(gender IN ('M','F')),
                looking_for  TEXT CHECK(looking_for IN ('M','F','A')),
                city         TEXT,
                bio          TEXT,
                photo_id     TEXT,
                latitude     REAL,
                longitude    REAL,
                is_active    INTEGER DEFAULT 1,
                is_banned    INTEGER DEFAULT 0,
                is_premium   INTEGER DEFAULT 0,
                language     TEXT DEFAULT 'uz',
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS likes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id   INTEGER NOT NULL,
                is_like      INTEGER NOT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(from_user_id, to_user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_likes_from ON likes(from_user_id);
            CREATE INDEX IF NOT EXISTS idx_likes_to ON likes(to_user_id);

            CREATE TABLE IF NOT EXISTS matches (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id   INTEGER NOT NULL,
                user2_id   INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active  INTEGER DEFAULT 1,
                UNIQUE(user1_id, user2_id)
            );

            CREATE INDEX IF NOT EXISTS idx_matches_users
                ON matches(user1_id, user2_id);

            CREATE TABLE IF NOT EXISTS reports (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL,
                to_user_id   INTEGER NOT NULL,
                reason       TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS active_chats (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL UNIQUE,
                partner_id INTEGER NOT NULL,
                match_id   INTEGER NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bot_settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admin_logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id   INTEGER NOT NULL,
                action     TEXT NOT NULL,
                target_id  INTEGER,
                details    TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS admins (
                user_id    INTEGER PRIMARY KEY,
                role       TEXT NOT NULL DEFAULT 'admin',
                added_by   INTEGER,
                added_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- ============ MONITORING SYSTEM V3 ============

            -- Event logs: barcha foydalanuvchi amallari
            CREATE TABLE IF NOT EXISTS logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                metadata   TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_logs_user_id
                ON logs(user_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_logs_event_type
                ON logs(event_type, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_logs_created_at
                ON logs(created_at DESC);

            -- Avtomatik alerts (shubhali foydalanuvchilar)
            CREATE TABLE IF NOT EXISTS alerts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                reason     TEXT NOT NULL,
                status     TEXT NOT NULL DEFAULT 'pending',
                details    TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_alerts_status
                ON alerts(status, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_alerts_user_id
                ON alerts(user_id, status);

            -- Shikoyat qilingan suhbat xabarlari (faqat report bo'lganda saqlanadi)
            CREATE TABLE IF NOT EXISTS reported_messages (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id    INTEGER NOT NULL,
                sender_id    INTEGER NOT NULL,
                message_type TEXT NOT NULL,
                content      TEXT,
                file_id      TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_reported_messages_report
                ON reported_messages(report_id);

            -- admin_logs jadvalida yaxshilangan indeks
            CREATE INDEX IF NOT EXISTS idx_admin_logs_target
                ON admin_logs(target_id, created_at DESC);

            -- ============ CHAT MODERATION SYSTEM ============

            -- Foydalanuvchining qoidabuzarliklari (filter trigger bo'lganda)
            CREATE TABLE IF NOT EXISTS violations (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                reason       TEXT NOT NULL,
                message_text TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_violations_user_id
                ON violations(user_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_admin_logs_admin
                ON admin_logs(admin_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_reports_to
                ON reports(to_user_id);
            """
        )
        await db.commit()

        # Eski DB uchun migration: yetishmagan ustunlarni qo'shamiz
        cursor = await db.execute("PRAGMA table_info(users)")
        existing_cols = {row[1] for row in await cursor.fetchall()}
        for col, sql in (
            ("latitude", "ALTER TABLE users ADD COLUMN latitude REAL"),
            ("longitude", "ALTER TABLE users ADD COLUMN longitude REAL"),
            ("is_shadow_banned", "ALTER TABLE users ADD COLUMN is_shadow_banned INTEGER DEFAULT 0"),
            ("premium_until", "ALTER TABLE users ADD COLUMN premium_until TIMESTAMP"),
            ("is_verified", "ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0"),
            ("voice_id", "ALTER TABLE users ADD COLUMN voice_id TEXT"),
            ("muted_until", "ALTER TABLE users ADD COLUMN muted_until TIMESTAMP"),
            ("safety_agreed_at", "ALTER TABLE users ADD COLUMN safety_agreed_at TIMESTAMP"),
        ):
            if col not in existing_cols:
                await db.execute(sql)
        await db.commit()

        # reports jadvalida status ustuni
        cursor = await db.execute("PRAGMA table_info(reports)")
        report_cols = {row[1] for row in await cursor.fetchall()}
        if "status" not in report_cols:
            await db.execute("ALTER TABLE reports ADD COLUMN status TEXT DEFAULT 'pending'")
        await db.commit()

        # Default sozlamalar
        defaults = {
            "registration_enabled": "1",
            "auto_ban_enabled": "1",
            "auto_ban_threshold": "3",
            "min_age": "14",
            "daily_likes_limit": "0",  # 0 = cheksiz
            "flood_limit": "0",  # 0 = default throttling
            # Premium narxi va karta — admin paneldan tahrirlanadi
            "premium_price": "9 999 so'm",
            "premium_card": "5614 6847 0909 0318",
            "premium_days": "30",
            "premium_card_holder": "Tanishuv Bot",  # karta egasining ismi
        }
        for k, v in defaults.items():
            await db.execute(
                "INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)",
                (k, v),
            )
        await db.commit()

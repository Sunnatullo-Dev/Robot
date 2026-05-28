import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str
    admin_ids: list[int]
    db_path: str
    channel_username: str
    require_subscription: bool


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(".env faylida BOT_TOKEN ko'rsatilmagan")

    admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()
    admin_ids = [int(x) for x in admin_ids_raw.split(",") if x.strip().isdigit()]

    return Config(
        bot_token=token,
        admin_ids=admin_ids,
        db_path=os.getenv("DB_PATH", "tanishuv.db"),
        channel_username=os.getenv("CHANNEL_USERNAME", "").strip(),
        require_subscription=os.getenv("REQUIRE_SUBSCRIPTION", "false").lower() == "true",
    )

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, ErrorEvent, Message

from config import load_config
from database import models
from database.db import init_db
from handlers import (
    admin,
    admin_alerts,
    admin_monitoring,
    admin_timeline,
    chat,
    matches,
    premium,
    profile,
    registration,
    search,
    start,
)
from middlewares.banned import BannedMiddleware
from middlewares.throttling import ThrottlingMiddleware


def _build_fallback_router() -> Router:
    """Eng oxirgi router — boshqalar tushira olmagan callback va xatolarni
    silliq ishlatish uchun.
    """
    r = Router(name="fallback")

    @r.callback_query()
    async def stale_callback(call: CallbackQuery) -> None:
        # Hech qanday handler tushira olmagan eski tugma — sticker emas, foydalanuvchi
        # eski xabardagi tugmani bosgan bo'lishi mumkin
        await call.answer(
            "⌛ Bu tugma muddati o'tdi yoki bekor qilingan. /start bilan qaytadan boshlang.",
            show_alert=True,
        )

    return r


async def _on_error(event: ErrorEvent) -> None:
    """Global xato ushlovchi — botning faollik holatini buzmaslik uchun."""
    logging.exception("Unhandled exception: %s", event.exception)
    msg = event.update.message or (
        event.update.callback_query.message if event.update.callback_query else None
    )
    if isinstance(msg, Message):
        try:
            await msg.answer("❗️ Texnik xatolik yuz berdi. Birozdan keyin qaytadan urinib ko'ring.")
        except (TelegramBadRequest, TelegramForbiddenError):
            pass


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    config = load_config()
    await init_db(config.db_path)
    await models.ensure_owners(config.admin_ids)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp["config"] = config

    # Bloklangan foydalanuvchilarni ushlash — boshqa hech narsaga o'tkazmaslik
    dp.message.middleware(BannedMiddleware())
    dp.callback_query.middleware(BannedMiddleware())

    dp.message.middleware(ThrottlingMiddleware(rate_limit=0.5))
    dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=0.3))

    dp.errors.register(_on_error)

    dp.include_routers(
        start.router,
        registration.router,
        profile.router,
        search.router,
        matches.router,
        premium.router,  # MUHIM: chat.router'dan oldin (dm:, prem: callbacklar)
        chat.router,
        # Admin Monitoring V3 — admin.router'dan oldin (mon:, alrt:, tl: callbacks)
        admin_monitoring.router,
        admin_alerts.router,
        admin_timeline.router,
        admin.router,
        _build_fallback_router(),  # OXIRGI: eski tugmalar uchun
    )

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot ishga tushdi")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")
        sys.exit(0)

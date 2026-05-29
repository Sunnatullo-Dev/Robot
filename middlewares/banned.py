"""Bloklangan foydalanuvchilarni butun botdan to'sib qo'yadigan middleware."""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from database import models


class BannedMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None and await models.is_banned(user.id):
            if isinstance(event, Message):
                await event.answer("🚫 Siz botdan foydalanish huquqidan mahrum etilgansiz.")
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫 Sizga ruxsat berilmagan.", show_alert=True)
            return None
        return await handler(event, data)

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5) -> None:
        self.rate_limit = rate_limit
        self._last: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None:
            now = time.monotonic()
            last = self._last.get(user.id, 0.0)
            if now - last < self.rate_limit:
                return None
            self._last[user.id] = now
        return await handler(event, data)

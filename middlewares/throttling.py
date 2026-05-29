import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """Bir foydalanuvchidan kelayotgan tezkor takroriy so'rovlarni cheklaydi.

    Xotira to'ldirilib ketmasligi uchun har 1000 ta yozuvda eski (2 daqiqadan
    eski) yozuvlar tozalanadi.
    """

    def __init__(self, rate_limit: float = 0.5) -> None:
        self.rate_limit = rate_limit
        self._last: dict[int, float] = {}

    def _gc_if_needed(self, now: float) -> None:
        if len(self._last) > 1000:
            cutoff = now - 120
            self._last = {uid: t for uid, t in self._last.items() if t >= cutoff}

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
            self._gc_if_needed(now)
        return await handler(event, data)

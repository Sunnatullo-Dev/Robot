"""High-level logging service.

Foydalanuvchi event'larini yozish va alert qoidalarini tekshirish
uchun bir yagona API. Handler'lar mana shu funksiyani chaqirishadi.

Production qoidalar:
- Exception'lar handler'ga yetib bormaydi (log qilinadi, lekin asosiy
  oqim to'xtatilmaydi).
- DB xatosi botning ishini buzmaydi.
- Asinxron — UI ni bloklamaydi.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from database import logs
from services.alert_service import check_and_create_alert

logger = logging.getLogger(__name__)


async def log_event(
    user_id: int,
    event_type: str,
    metadata: Optional[dict[str, Any]] = None,
    check_alerts: bool = True,
) -> None:
    """Event'ni yozish + (ixtiyoriy) alert qoidalarini tekshirish.

    Bu funksiya hech qachon exception ko'tarmaydi — barcha xatolar
    log qilinadi va sukut bilan o'tib ketadi.

    Args:
        user_id: Telegram foydalanuvchi ID
        event_type: logs.EventType konstantalaridan biri
        metadata: JSON-serializable qo'shimcha ma'lumot
        check_alerts: Avtomatik alert tekshirishni yoqib qo'yish (default: True)
    """
    try:
        await logs.log_event(user_id, event_type, metadata)
    except Exception as e:  # noqa: BLE001
        logger.exception("Failed to log event %s for u=%s: %s", event_type, user_id, e)
        return

    if check_alerts:
        try:
            await check_and_create_alert(user_id, event_type)
        except Exception as e:  # noqa: BLE001
            logger.exception("Alert check failed: %s", e)

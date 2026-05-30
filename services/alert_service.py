"""Alert service — shubhali xulq-atvorni avtomatik aniqlash.

Har bir event qabul qilinganda, mana shu service tegishli qoidani
tekshiradi va kerak bo'lsa avtomatik alert yaratadi.

Qoidalar oson kengaytirilishi mumkin — ALERT_RULES'ga qatorni qo'shing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from database import alerts, logs

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlertRule:
    """Bitta event'ning chegarasini belgilash."""

    event_type: str
    window_minutes: int  # 0 = all-time
    threshold: int
    reason: str
    template: str  # "{count} ta {event} {window} daqiqada"


# Tayyor qoidalar — Spec'ga muvofiq
ALERT_RULES: tuple[AlertRule, ...] = (
    AlertRule(
        event_type=logs.EventType.LIKE_SENT,
        window_minutes=5,
        threshold=50,
        reason=alerts.AlertReason.TOO_MANY_LIKES,
        template="{count} ta like 5 daqiqada",
    ),
    AlertRule(
        event_type=logs.EventType.PROFILE_UPDATED,
        window_minutes=60,
        threshold=10,
        reason=alerts.AlertReason.TOO_MANY_PROFILE_CHANGES,
        template="{count} marta 1 soat ichida profilni o'zgartirgan",
    ),
    AlertRule(
        event_type=logs.EventType.REPORT_CREATED,
        window_minutes=0,  # all-time
        threshold=5,
        reason=alerts.AlertReason.TOO_MANY_REPORTS,
        template="{count} ta shikoyat olgan",
    ),
)


# Lookup uchun event_type → list[AlertRule]
_RULES_BY_EVENT: dict[str, list[AlertRule]] = {}
for r in ALERT_RULES:
    _RULES_BY_EVENT.setdefault(r.event_type, []).append(r)


async def check_and_create_alert(user_id: int, event_type: str) -> Optional[int]:
    """Ushbu event uchun qoidalarni tekshirib, kerakli alertni yaratish.

    Returns: yaratilgan alert ID yoki None.
    """
    rules = _RULES_BY_EVENT.get(event_type)
    if not rules:
        return None

    for rule in rules:
        # NOTE: Report kelganda event_type=REPORT_CREATED user_id'si
        # report-qilingan foydalanuvchi bo'lishi kerak (to_user_id).
        # Bu logging_service tomonidan to'g'ri uzatilishi kerak.
        if rule.window_minutes > 0:
            count = await logs.count_events_in_window(
                user_id, event_type, rule.window_minutes
            )
        else:
            count = await logs.count_events_total(user_id, event_type)

        if count >= rule.threshold:
            details = rule.template.format(
                count=count, event=event_type, window=rule.window_minutes,
            )
            alert_id = await alerts.create_alert(user_id, rule.reason, details)
            logger.info(
                "Alert created: u=%s reason=%s count=%s",
                user_id, rule.reason, count,
            )
            return alert_id

    return None

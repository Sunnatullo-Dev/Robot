"""In-memory chat buffer — har bir foydalanuvchining oxirgi 100 xabari.

Asosiy g'oya: oddiy chatlarni DB ga yozmang. Buning o'rniga oxirgi xabarlarni
xotirada (RAM) saqlang. Foydalanuvchi report bossagina, partner'ning oxirgi
xabarlari DB ga ko'chiriladi (`reported_messages` jadvali).

Bu juda katta server tejaydi (10k+ chat = ko'p IO). RAM ishlatamiz.

Memory:
- max 100 ta xabar / user
- har biri ~200-500 bayt
- 1000 ta faol foydalanuvchi = ~50 MB RAM
- Chat tugaganda buffer tozalanadi
"""
from __future__ import annotations

import time
from collections import deque
from typing import Any

MAX_MESSAGES_PER_USER = 100


# user_id -> deque of message dicts
_buffers: dict[int, deque[dict[str, Any]]] = {}


def append(
    user_id: int,
    msg_type: str,
    content: str = "",
    file_id: str = "",
) -> None:
    """Foydalanuvchining buffer'iga xabar qo'shish.

    Args:
        user_id: kim yubordi
        msg_type: 'text', 'photo', 'voice', 'video_note', 'sticker', 'document'
        content: matn (text, caption) — maksimal 500 belgi saqlanadi
        file_id: media file_id (rasmlar/ovozlar/stikerlar uchun)
    """
    buf = _buffers.setdefault(user_id, deque(maxlen=MAX_MESSAGES_PER_USER))
    buf.append({
        "type": msg_type,
        "content": (content or "")[:500],
        "file_id": file_id or "",
        "ts": int(time.time()),
    })


def get_messages(user_id: int, limit: int = 100) -> list[dict[str, Any]]:
    """Foydalanuvchi'ning oxirgi N xabarini olish (eng yangidan boshlab)."""
    buf = _buffers.get(user_id)
    if not buf:
        return []
    return list(buf)[-limit:]


def clear(user_id: int) -> None:
    """Foydalanuvchining buffer'ini tozalash (chat tugaganda)."""
    _buffers.pop(user_id, None)


def stats() -> dict[str, int]:
    """RAM ishlatish statistikasi (debug uchun)."""
    return {
        "users": len(_buffers),
        "total_messages": sum(len(b) for b in _buffers.values()),
    }

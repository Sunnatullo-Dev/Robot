import html
import math
from typing import Any, Optional


def esc(text: Optional[str]) -> str:
    """HTML escape — foydalanuvchi matnidagi <, >, & belgilarni xavfsiz qiladi."""
    if not text:
        return ""
    return html.escape(str(text), quote=False)


def gender_text(code: str) -> str:
    return {"M": "Erkak", "F": "Ayol", "A": "Farqi yo'q"}.get(code, "—")


def gender_emoji(code: str) -> str:
    return {"M": "👨", "F": "👩"}.get(code, "🧑")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Ikki nuqta orasidagi masofa (kilometr)."""
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def format_distance(km: float) -> str:
    if km < 1:
        return "1 km dan yaqin"
    if km < 10:
        return f"~{km:.1f} km"
    if km < 1000:
        return f"~{int(round(km))} km"
    return f"{int(round(km / 1000))} ming km+"


def format_profile(user: dict[str, Any], distance_km: Optional[float] = None) -> str:
    name = esc(user.get("name")) or "—"
    age = user.get("age") or "—"
    city = esc(user.get("city")) or "—"
    bio = esc(user.get("bio"))
    g = user.get("gender") or ""

    text = (
        f"{gender_emoji(g)} <b>{name}</b>, {age} yosh\n"
        f"🏙 {city}"
    )
    if distance_km is not None:
        text += f"\n📍 {format_distance(distance_km)} uzoqlikda"
    if bio:
        text += f"\n\n💬 {bio}"
    return text


def parse_age(text: str) -> int | None:
    text = text.strip()
    if not text.isdigit():
        return None
    age = int(text)
    if age < 14 or age > 99:
        return None
    return age

from typing import Any


def gender_text(code: str) -> str:
    return {"M": "Erkak", "F": "Ayol", "A": "Farqi yo'q"}.get(code, "—")


def gender_emoji(code: str) -> str:
    return {"M": "👨", "F": "👩"}.get(code, "🧑")


def format_profile(user: dict[str, Any]) -> str:
    name = user.get("name") or "—"
    age = user.get("age") or "—"
    city = user.get("city") or "—"
    bio = user.get("bio") or ""
    g = user.get("gender") or ""

    text = (
        f"{gender_emoji(g)} <b>{name}</b>, {age} yosh\n"
        f"📍 {city}"
    )
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

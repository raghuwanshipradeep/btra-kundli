from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData

EXALTATION = {
    "Sun": "Aries", "Moon": "Taurus", "Mars": "Capricorn",
    "Mercury": "Virgo", "Jupiter": "Cancer", "Venus": "Pisces",
    "Saturn": "Libra", "Rahu": "Taurus", "Ketu": "Scorpio",
}

DEBILITATION = {
    "Sun": "Libra", "Moon": "Scorpio", "Mars": "Cancer",
    "Mercury": "Pisces", "Jupiter": "Capricorn", "Venus": "Virgo",
    "Saturn": "Aries", "Rahu": "Scorpio", "Ketu": "Taurus",
}

OWN_SIGNS: dict[str, list[str]] = {
    "Sun": ["Leo"],
    "Moon": ["Cancer"],
    "Mars": ["Aries", "Scorpio"],
    "Mercury": ["Gemini", "Virgo"],
    "Jupiter": ["Sagittarius", "Pisces"],
    "Venus": ["Taurus", "Libra"],
    "Saturn": ["Capricorn", "Aquarius"],
    "Rahu": ["Aquarius"],
    "Ketu": ["Scorpio"],
}

MOOLATRIKONA = {
    "Sun": "Leo", "Moon": "Taurus", "Mars": "Aries",
    "Mercury": "Virgo", "Jupiter": "Sagittarius", "Venus": "Libra",
    "Saturn": "Aquarius",
}


def _get_dignity(name: str, sign: str) -> str:
    if EXALTATION.get(name) == sign:
        return "Exalted"
    if DEBILITATION.get(name) == sign:
        return "Debilitated"
    if MOOLATRIKONA.get(name) == sign:
        return "Moolatrikona"
    if sign in OWN_SIGNS.get(name, []):
        return "Own Sign"
    return "Normal"


def render_dignity(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    rows = []
    for p in data.planets:
        if p.name == "Ascendant":
            continue
        dignity = _get_dignity(p.name, p.sign)
        rows.append({
            "planet": p.name,
            "sign": p.sign,
            "dignity": dignity,
            "retro": p.isRetro == "true",
        })

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("dignity.html")
    return template.render(
        dignity_rows=rows,
        locale=locale,
        lang=lang,
    )

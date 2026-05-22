from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData


def render_three_pillars(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    ascendant = next((p for p in data.planets if p.name == "Ascendant"), None)
    moon = next((p for p in data.planets if p.name == "Moon"), None)
    if not ascendant and not moon:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])

    lagna_info = None
    if ascendant:
        lagna_info = {
            "sign": locale.get("sign_names", {}).get(ascendant.sign, ascendant.sign),
            "lord": locale.get("planet_names", {}).get(ascendant.signLord, ascendant.signLord),
            "nakshatra": ascendant.nakshatra,
            "degree": round(ascendant.normDegree, 2),
        }

    moon_info = None
    if moon:
        moon_info = {
            "sign": locale.get("sign_names", {}).get(moon.sign, moon.sign),
            "lord": locale.get("planet_names", {}).get(moon.signLord, moon.signLord),
            "house": moon.house,
            "nakshatra": moon.nakshatra,
        }

    nakshatra_info = None
    if moon:
        nakshatra_info = {
            "nakshatra": moon.nakshatra,
            "lord": locale.get("planet_names", {}).get(moon.nakshatraLord, moon.nakshatraLord),
            "pada": moon.nakshatra_pad,
            "sign": locale.get("sign_names", {}).get(moon.sign, moon.sign),
        }

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("three_pillars.html")
    return template.render(
        lagna=lagna_info,
        moon_rashi=moon_info,
        nakshatra=nakshatra_info,
        narratives=data.narratives,
        locale=locale,
        lang=lang,
    )

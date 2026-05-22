from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import (
    LOCALES,
    PLANET_SHORT_EN,
    PLANET_SHORT_HI,
    build_sign_planet_map,
)

if TYPE_CHECKING:
    from models import KundliData

SOUTH_INDIAN_FIXED_SIGNS = [
    "Pisces", "Aries", "Taurus", "Gemini",
    "Aquarius", None, None, "Cancer",
    "Capricorn", None, None, "Leo",
    "Sagittarius", "Scorpio", "Libra", "Virgo",
]

SOUTH_GRID_POSITIONS = [
    (0, 0), (0, 1), (0, 2), (0, 3),
    (1, 0), None,   None,   (1, 3),
    (2, 0), None,   None,   (2, 3),
    (3, 0), (3, 1), (3, 2), (3, 3),
]


def render_south_chart(data: KundliData, lang: str = "en") -> str | None:
    if not data.horo_chart_d1 and not data.planets:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    short = PLANET_SHORT_HI if lang == "hi" else PLANET_SHORT_EN

    sign_planets: dict[str, list[str]] = {}
    if data.horo_chart_d1:
        for entry in data.horo_chart_d1:
            if entry.planet:
                localized = [short.get(p, p) for p in entry.planet]
                sign_planets[entry.sign_name] = localized
            else:
                sign_planets[entry.sign_name] = []

    if not any(sign_planets.values()) and data.planets:
        sign_planets = build_sign_planet_map(data.planets, lang)

    lagna_sign: str | None = None
    if data.planets:
        asc = next((p for p in data.planets if p.name == "Ascendant"), None)
        if asc:
            lagna_sign = asc.sign

    cells = []
    for i, sign_name in enumerate(SOUTH_INDIAN_FIXED_SIGNS):
        if sign_name is None:
            continue
        planets = sign_planets.get(sign_name, [])
        cells.append({
            "sign": sign_name,
            "sign_abbr": sign_name[:3],
            "planets": planets,
            "row": SOUTH_GRID_POSITIONS[i][0],
            "col": SOUTH_GRID_POSITIONS[i][1],
            "is_lagna": sign_name == lagna_sign,
        })

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("south_chart.html")
    return template.render(
        cells=cells,
        locale=locale,
        lang=lang,
    )

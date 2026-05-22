from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData

KARAKA_NAMES = [
    "Atmakaraka",
    "Amatyakaraka",
    "Bhratrikaraka",
    "Matrikaraka",
    "Putrakaraka",
    "Gnatikaraka",
    "Darakaraka",
]

JAIMINI_PLANETS = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"}


def render_chara_karaka(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    candidates = [p for p in data.planets if p.name in JAIMINI_PLANETS]
    if len(candidates) < 7:
        return None

    for p in candidates:
        if p.name == "Rahu":
            p._adj_degree = 30.0 - p.normDegree
        else:
            p._adj_degree = p.normDegree

    sorted_planets = sorted(candidates, key=lambda p: p._adj_degree, reverse=True)

    rows = []
    for i, karaka_name in enumerate(KARAKA_NAMES):
        if i < len(sorted_planets):
            p = sorted_planets[i]
            rows.append({
                "karaka": karaka_name,
                "planet": p.name,
                "degree": round(p.normDegree, 2),
                "sign": p.sign,
            })

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("chara_karaka.html")
    return template.render(
        karaka_rows=rows,
        locale=locale,
        lang=lang,
    )

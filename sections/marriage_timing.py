from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData

MARRIAGE_PLANETS = {"Venus", "Jupiter", "Moon"}
SEVENTH_HOUSE_NUM = 7


def render_marriage_timing(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets or not data.houses or not data.major_vdasha:
        return None

    h7 = next((h for h in data.houses if h.house_id == 7), None)
    if not h7:
        return None

    seventh_lord = h7.sign_lord
    venus = next((p for p in data.planets if p.name == "Venus"), None)

    factors = []
    factors.append({
        "factor": "7th House Sign",
        "value": h7.sign,
        "significance": "The sign in the 7th house shapes partnership dynamics.",
    })
    factors.append({
        "factor": "7th Lord",
        "value": seventh_lord,
        "significance": f"{seventh_lord} governs marriage prospects through its placement and strength.",
    })

    seventh_lord_planet = next((p for p in data.planets if p.name == seventh_lord), None)
    if seventh_lord_planet:
        factors.append({
            "factor": "7th Lord Placement",
            "value": f"House {seventh_lord_planet.house} in {seventh_lord_planet.sign}",
            "significance": "Position of 7th lord indicates the nature and timing of marriage.",
        })

    if venus:
        factors.append({
            "factor": "Venus Position",
            "value": f"House {venus.house} in {venus.sign}",
            "significance": "Venus as natural karaka of marriage influences romantic tendencies.",
        })

    favorable_periods = []
    for dasha in data.major_vdasha:
        if dasha.planet in (seventh_lord, "Venus", "Jupiter"):
            favorable_periods.append({
                "planet": dasha.planet,
                "start": dasha.start,
                "end": dasha.end,
                "reason": f"{dasha.planet} Mahadasha — connected to marriage significations.",
            })

    planets_in_7 = [p.name for p in data.planets if p.house == 7 and p.name != "Ascendant"]

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("marriage_timing.html")
    return template.render(
        factors=factors,
        favorable_periods=favorable_periods,
        planets_in_7=planets_in_7,
        narrative=data.narratives.get("marriage_timing", ""),
        locale=locale,
        lang=lang,
    )

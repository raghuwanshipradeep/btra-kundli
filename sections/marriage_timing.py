from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env, planet_to_en
from sections.life_area_remedies import build_area_remedies

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

    locale = LOCALES.get(lang, LOCALES["en"])
    sign_names = locale.get("sign_names", {})
    planet_names = locale.get("planet_names", {})

    def loc_sign(s: str) -> str:
        return sign_names.get(s, s)

    def loc_planet(p: str) -> str:
        return planet_names.get(p, p)

    placement_fmt = locale.get("mt_placement_fmt", "House {house} in {sign}")
    seventh_lord_loc = loc_planet(seventh_lord)

    factors = []
    factors.append({
        "factor": locale.get("mt_factor_7th_sign", "7th House Sign"),
        "value": loc_sign(h7.sign),
        "significance": locale.get(
            "mt_sig_7th_sign",
            "The sign in the 7th house shapes partnership dynamics.",
        ),
    })
    factors.append({
        "factor": locale.get("mt_factor_7th_lord", "7th Lord"),
        "value": seventh_lord_loc,
        "significance": locale.get(
            "mt_sig_7th_lord",
            "{planet} governs marriage prospects through its placement and strength.",
        ).format(planet=seventh_lord_loc),
    })

    seventh_lord_planet = next((p for p in data.planets if p.name == seventh_lord), None)
    if seventh_lord_planet:
        factors.append({
            "factor": locale.get("mt_factor_7th_lord_placement", "7th Lord Placement"),
            "value": placement_fmt.format(
                house=seventh_lord_planet.house, sign=loc_sign(seventh_lord_planet.sign)
            ),
            "significance": locale.get(
                "mt_sig_7th_lord_placement",
                "Position of 7th lord indicates the nature and timing of marriage.",
            ),
        })

    if venus:
        factors.append({
            "factor": locale.get("mt_factor_venus", "Venus Position"),
            "value": placement_fmt.format(house=venus.house, sign=loc_sign(venus.sign)),
            "significance": locale.get(
                "mt_sig_venus",
                "Venus as natural karaka of marriage influences romantic tendencies.",
            ),
        })

    reason_fmt = locale.get(
        "mt_favorable_reason",
        "{planet} Mahadasha — connected to marriage significations.",
    )
    favorable_periods = []
    for dasha in data.major_vdasha:
        planet_en = planet_to_en(dasha.planet)
        if planet_en in (seventh_lord, "Venus", "Jupiter"):
            favorable_periods.append({
                "planet": planet_en,
                "start": dasha.start,
                "end": dasha.end,
                "reason": reason_fmt.format(planet=loc_planet(planet_en)),
            })

    planets_in_7 = [p.name for p in data.planets if p.house == 7 and p.name != "Ascendant"]

    env = make_env()
    template = env.get_template("marriage_timing.html")
    return template.render(
        factors=factors,
        favorable_periods=favorable_periods,
        planets_in_7=planets_in_7,
        remedies=build_area_remedies(data, [seventh_lord, "Venus"], lang),
        narrative=data.narratives.get("marriage_timing", ""),
        locale=locale,
        lang=lang,
    )

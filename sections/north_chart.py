from __future__ import annotations

import logging
from typing import TYPE_CHECKING


from sections import (
    LOCALES,
    SIGN_NAMES_BY_ID,
    SIGN_ORDER_EN,
    PLANET_SHORT_EN,
    PLANET_SHORT_HI,
    build_sign_planet_map,
    get_north_indian_sign_for_house,
    make_env,
    planet_to_en,
)

if TYPE_CHECKING:
    from models import KundliData

logger = logging.getLogger(__name__)

# House positions in the 0-400 chart space. Traditional North Indian layout:
# house 1 fixed at top-center and houses run ANTI-CLOCKWISE (house 2 top-left,
# house 12 top-right), so rashi numbers and their planets increase anti-clockwise.
HOUSE_CENTROIDS = {
    1: (200, 75),
    2: (100, 33),
    3: (33, 100),
    4: (75, 200),
    5: (33, 300),
    6: (100, 367),
    7: (200, 325),
    8: (300, 367),
    9: (367, 300),
    10: (325, 200),
    11: (367, 100),
    12: (300, 33),
}


OUTER_PLANETS_EN = ("Uranus", "Neptune", "Pluto")


def _build_detailed_sign_map(data: KundliData, short: dict) -> dict[int, list[dict]]:
    """Sign id -> [{label, deg}] built from planet positions + outer planets, with
    per-planet degrees. Grahas come from data.planets (authoritative); Uranus/
    Neptune/Pluto are pulled from data.planets_extended. Ascendant is excluded (it
    is drawn separately as लग्न). Degrees are whole numbers, matching the reference."""
    result: dict[int, list[dict]] = {}
    seen: set[str] = set()
    combined = list(data.planets or []) + list(data.planets_extended or [])
    for p in combined:
        name_en = planet_to_en(p.name)
        if name_en == "Ascendant" or name_en in seen:
            continue
        if p.sign not in SIGN_ORDER_EN:
            continue
        seen.add(name_en)
        sid = SIGN_ORDER_EN.index(p.sign) + 1
        result.setdefault(sid, []).append({
            "label": short.get(name_en, name_en),
            "deg": int(p.normDegree),
        })
    return result


def build_lagna_houses(
    data: KundliData, lang: str, locale: dict, with_details: bool = False
) -> list | None:
    """Build the 12-house North Indian (diamond) layout for the D1 lagna chart.

    Returns the house list for `partials/north_indian_chart.html`, or None when
    the ascendant can't be determined. Reused by the panchang page (which embeds
    the lagna chart right after the birth-panchang table).

    When `with_details` is True, each house's `planets` is a list of
    `{label, deg}` dicts including the outer planets (Uranus/Neptune/Pluto) and
    per-planet degrees; otherwise it stays a plain list of short-label strings
    (the compact form used by the panchang embed and divisional charts).
    """
    if not data.planets:
        logger.debug("north_chart: no planets data")
        return None

    short = PLANET_SHORT_HI if lang == "hi" else PLANET_SHORT_EN

    asc = next(
        (p for p in data.planets if p.name == "Ascendant"),
        next((p for p in data.planets if p.id == 9), None),
    )
    if not asc:
        logger.debug("north_chart: Ascendant not found (by name or id=9)")
        return None
    if asc.sign not in SIGN_ORDER_EN:
        logger.debug("north_chart: Ascendant sign %r not in SIGN_ORDER_EN", asc.sign)
        return None
    lagna_sign_id = SIGN_ORDER_EN.index(asc.sign) + 1

    # Key by sign id (language-independent); the API localizes sign_name and
    # planet labels for Hindi PDFs, so normalize planets to English canonical
    # names before mapping to short forms.
    sign_planet_map: dict[int, list] = {}
    if with_details:
        sign_planet_map = _build_detailed_sign_map(data, short)
    else:
        if data.horo_chart_d1:
            for entry in data.horo_chart_d1:
                if entry.planet and entry.sign:
                    en_planets = [planet_to_en(p) for p in entry.planet]
                    sign_planet_map[entry.sign] = [short.get(p, p) for p in en_planets]
        if not sign_planet_map:
            # Fallback: derive from planet positions (keyed by English sign name).
            name_map = build_sign_planet_map(data.planets, lang)
            for sname, plist in name_map.items():
                if sname in SIGN_ORDER_EN:
                    sign_planet_map[SIGN_ORDER_EN.index(sname) + 1] = plist

    sign_names_by_id = locale.get("sign_names_by_id", {})
    houses = []
    for h in range(1, 13):
        sid = get_north_indian_sign_for_house(h, lagna_sign_id)
        sign_name_en = SIGN_NAMES_BY_ID[sid]
        sign_name_local = sign_names_by_id.get(sid, sign_name_en)
        planets_in_house = sign_planet_map.get(sid, [])
        cx, cy = HOUSE_CENTROIDS[h]
        houses.append({
            "house": h,
            "sign_id": sid,
            "sign_name": sign_name_local,
            "planets": planets_in_house,
            "cx": cx,
            "cy": cy,
        })
    return houses


def render_north_chart(data: KundliData, lang: str = "en") -> str | None:
    locale = LOCALES.get(lang, LOCALES["en"])
    houses = build_lagna_houses(data, lang, locale, with_details=True)
    if not houses:
        return None

    env = make_env()
    template = env.get_template("north_chart.html")
    return template.render(
        houses=houses,
        locale=locale,
        lang=lang,
    )

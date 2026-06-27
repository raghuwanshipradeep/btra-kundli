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

HOUSE_CENTROIDS = {
    1: (200, 75),
    2: (300, 33),
    3: (367, 100),
    4: (325, 200),
    5: (367, 300),
    6: (300, 367),
    7: (200, 325),
    8: (100, 367),
    9: (33, 300),
    10: (75, 200),
    11: (33, 100),
    12: (100, 33),
}


def render_north_chart(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        logger.debug("north_chart: no planets data")
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
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
    sign_planet_map: dict[int, list[str]] = {}
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

    houses = []
    for h in range(1, 13):
        sid = get_north_indian_sign_for_house(h, lagna_sign_id)
        sign_name_en = SIGN_NAMES_BY_ID[sid]
        sign_names_by_id = locale.get("sign_names_by_id", {})
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

    env = make_env()
    template = env.get_template("north_chart.html")
    return template.render(
        houses=houses,
        lagna_sign_id=lagna_sign_id,
        locale=locale,
        lang=lang,
    )

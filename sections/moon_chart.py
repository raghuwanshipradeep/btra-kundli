from __future__ import annotations

import logging
from typing import TYPE_CHECKING


from sections import LOCALES, SIGN_ORDER_EN, make_env

if TYPE_CHECKING:
    from models import KundliData

logger = logging.getLogger(__name__)


def render_moon_chart(data: KundliData, lang: str = "en") -> str | None:
    if not data.horo_chart_d1 or not data.planets:
        logger.debug("moon_chart: horo_chart_d1=%s, planets=%s", bool(data.horo_chart_d1), bool(data.planets))
        return None

    moon = next(
        (p for p in data.planets if p.name == "Moon"),
        next((p for p in data.planets if p.id == 1), None),
    )
    if not moon:
        logger.debug("moon_chart: Moon planet not found in planets list")
        return None

    moon_sign = moon.sign
    if moon_sign not in SIGN_ORDER_EN:
        logger.debug("moon_chart: Moon sign %r not in SIGN_ORDER_EN", moon_sign)
        return None

    moon_idx = SIGN_ORDER_EN.index(moon_sign)
    d1_by_sign = {s.sign_name: s for s in data.horo_chart_d1}
    rotated = []
    for i in range(12):
        sign_name = SIGN_ORDER_EN[(moon_idx + i) % 12]
        entry = d1_by_sign.get(sign_name)
        if entry:
            rotated.append({
                "house": i + 1,
                "sign": sign_name,
                "planets": entry.planet if entry.planet else [],
            })
        else:
            rotated.append({"house": i + 1, "sign": sign_name, "planets": []})

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("moon_chart.html")
    return template.render(
        moon_chart=rotated,
        moon_sign=moon_sign,
        locale=locale,
        lang=lang,
    )

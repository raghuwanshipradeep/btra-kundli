from __future__ import annotations

import logging
from typing import TYPE_CHECKING


from sections import (
    LOCALES,
    SIGN_NAMES_BY_ID,
    SIGN_NAMES_HI_BY_ID,
    PLANET_SHORT_EN,
    PLANET_SHORT_HI,
    get_north_indian_sign_for_house,
    make_env,
)
from sections.north_chart import HOUSE_CENTROIDS

if TYPE_CHECKING:
    from models import KundliData

logger = logging.getLogger(__name__)

CHART_ORDER = [
    ("D2", "d2_title", "d2_desc"),
    ("D3", "d3_title", "d3_desc"),
    ("D4", "d4_title", "d4_desc"),
    ("D5", "d5_title", "d5_desc"),
    ("D7", "d7_title", "d7_desc"),
    ("D8", "d8_title", "d8_desc"),
    ("D9", "d9_title", "d9_desc"),
    ("D10", "d10_title", "d10_desc"),
    ("D12", "d12_title", "d12_desc"),
    ("D16", "d16_title", "d16_desc"),
    ("D20", "d20_title", "d20_desc"),
    ("D24", "d24_title", "d24_desc"),
    ("D27", "d27_title", "d27_desc"),
    ("D30", "d30_title", "d30_desc"),
    ("D40", "d40_title", "d40_desc"),
    ("D45", "d45_title", "d45_desc"),
    ("D60", "d60_title", "d60_desc"),
]


def build_chart_houses(chart_data, lang, locale):
    """Build a North Indian 12-house layout for one varga chart so it can be
    drawn as inline SVG (renders Hindi correctly), instead of the broken API image.

    Returns a list of house dicts (like north_chart.py), or None if the varga's
    ascendant sign can't be determined — in which case the caller falls back to
    the API image.
    """
    short = PLANET_SHORT_HI if lang == "hi" else PLANET_SHORT_EN

    sign_planet_map_en: dict[str, list[str]] = {}
    lagna_sign_id: int | None = None
    for entry in chart_data:
        sign_planet_map_en[entry.sign_name] = [short.get(p, p) for p in entry.planet]
        if any(p == "Ascendant" for p in entry.planet):
            lagna_sign_id = entry.sign

    if not lagna_sign_id:
        return None

    sign_names_by_id = locale.get("sign_names_by_id", {})
    houses = []
    for h in range(1, 13):
        sid = get_north_indian_sign_for_house(h, lagna_sign_id)
        sign_name_en = SIGN_NAMES_BY_ID[sid]
        cx, cy = HOUSE_CENTROIDS[h]
        houses.append({
            "house": h,
            "sign_id": sid,
            "sign_name": sign_names_by_id.get(sid, sign_name_en),
            "planets": sign_planet_map_en.get(sign_name_en, []),
            "cx": cx,
            "cy": cy,
        })
    return houses


def render_divisional_charts(data: KundliData, lang: str = "en") -> str | None:
    if not data.horo_charts:
        logger.debug("divisional_charts: horo_charts is empty/None")
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    images = data.horo_chart_images or {}

    logger.info("divisional_charts: horo_charts keys=%s, images keys=%s",
                list(data.horo_charts.keys()), list(images.keys()))

    charts = []
    for chart_id, title_key, desc_key in CHART_ORDER:
        chart_data = data.horo_charts.get(chart_id)
        if not chart_data:
            continue
        image_url = images.get(chart_id)
        signs_sorted = sorted(chart_data, key=lambda s: s.sign if hasattr(s, 'sign') else 0)
        houses = build_chart_houses(chart_data, lang, locale)
        logger.info("divisional_charts: %s → %d signs, houses=%s, image=%s",
                    chart_id, len(signs_sorted), "yes" if houses else "no",
                    "yes" if image_url else "no")
        charts.append({
            "id": chart_id,
            "title": locale.get(title_key, chart_id),
            "desc": locale.get(desc_key, ""),
            "signs": signs_sorted,
            "houses": houses,
            "image_url": image_url,
        })

    if not charts:
        return None

    logger.info("divisional_charts: rendering %d charts (%s)",
                len(charts), ", ".join(c["id"] for c in charts))

    env = make_env()
    template = env.get_template("divisional_charts.html")
    return template.render(
        charts=charts,
        sign_names_hi=SIGN_NAMES_HI_BY_ID,
        locale=locale,
        lang=lang,
    )

from __future__ import annotations

import logging
from typing import TYPE_CHECKING


from sections import LOCALES, SIGN_NAMES_HI_BY_ID, make_env

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
        logger.info("divisional_charts: %s → %d signs, image=%s",
                    chart_id, len(signs_sorted), "yes" if image_url else "no")
        charts.append({
            "id": chart_id,
            "title": locale.get(title_key, chart_id),
            "desc": locale.get(desc_key, ""),
            "signs": signs_sorted,
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

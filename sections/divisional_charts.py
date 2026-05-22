from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData

CHART_ORDER = [
    ("D9", "d9_title"),
    ("D3", "d3_title"),
    ("D7", "d7_title"),
    ("D10", "d10_title"),
    ("D2", "d2_title"),
    ("D4", "d4_title"),
    ("D5", "d5_title"),
    ("D8", "d8_title"),
    ("D12", "d12_title"),
    ("D16", "d16_title"),
    ("D20", "d20_title"),
    ("D24", "d24_title"),
    ("D27", "d27_title"),
    ("D30", "d30_title"),
    ("D40", "d40_title"),
    ("D45", "d45_title"),
    ("D60", "d60_title"),
]


def render_divisional_charts(data: KundliData, lang: str = "en") -> str | None:
    if not data.horo_charts:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])

    charts = []
    for chart_id, title_key in CHART_ORDER:
        chart_data = data.horo_charts.get(chart_id)
        if not chart_data:
            continue
        image_url = (data.horo_chart_images or {}).get(chart_id)
        charts.append({
            "id": chart_id,
            "title": locale.get(title_key, chart_id),
            "signs": chart_data,
            "image_url": image_url,
        })

    if not charts:
        return None

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("divisional_charts.html")
    return template.render(
        charts=charts,
        locale=locale,
        lang=lang,
    )

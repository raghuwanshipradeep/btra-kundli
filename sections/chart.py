from __future__ import annotations

import base64
from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_chart(data: KundliData, lang: str = "en") -> str | None:
    if not data.horo_chart_d1 and not data.natal_chart_svg:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("chart.html")

    chart_image: str | None = None
    if data.natal_chart_svg:
        svg_bytes = data.natal_chart_svg.encode("utf-8")
        b64 = base64.b64encode(svg_bytes).decode("ascii")
        chart_image = f"data:image/svg+xml;base64,{b64}"
    elif data.natal_wheel_chart and data.natal_wheel_chart.chart_url:
        chart_image = data.natal_wheel_chart.chart_url

    ascendant = None
    if data.planets:
        for p in data.planets:
            if p.name == "Ascendant":
                ascendant = p
                break

    return template.render(
        chart_image=chart_image,
        horo_chart=data.horo_chart_d1,
        ascendant=ascendant,
        locale=locale,
        lang=lang,
    )

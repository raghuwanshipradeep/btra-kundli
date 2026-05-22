from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES, SIGN_ORDER_EN

if TYPE_CHECKING:
    from models import KundliData

CONTRIBUTING_PLANETS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "ascendant"]


def render_bhinnashtak(data: KundliData, lang: str = "en") -> str | None:
    if not data.planet_ashtak:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    planet_names = locale.get("planet_names", {})

    sign_order = [locale["sign_names"].get(s, s) for s in SIGN_ORDER_EN]
    sign_keys = [s.lower() for s in SIGN_ORDER_EN]

    tables = []
    for pname, ashtak in data.planet_ashtak.items():
        display_name = planet_names.get(pname, pname)
        info = ashtak.ashtak_varga
        points = ashtak.ashtak_points

        rows = []
        for cp in CONTRIBUTING_PLANETS:
            cp_display = planet_names.get(cp.capitalize(), cp.capitalize())
            values = [points.get(sk, {}).get(cp, 0) for sk in sign_keys]
            total = sum(values)
            rows.append((cp_display, values, total))

        totals = [points.get(sk, {}).get("total", 0) for sk in sign_keys]
        grand_total = sum(totals)

        tables.append({
            "planet": display_name,
            "planet_en": pname,
            "info": info,
            "rows": rows,
            "totals": totals,
            "grand_total": grand_total,
        })

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("bhinnashtak.html")
    return template.render(
        tables=tables,
        sign_order=sign_order,
        locale=locale,
        lang=lang,
    )

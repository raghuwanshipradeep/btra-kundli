from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData


def render_numerology(data: KundliData, lang: str = "en") -> str | None:
    if (
        not data.numero_table
        and not data.numero_report
        and not data.numero_fav_time
        and not data.numero_fav_lord
        and not data.numero_fav_mantra
        and not data.numero_prediction_daily
    ):
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("numerology.html")
    return template.render(
        numero_table=data.numero_table,
        numero_report=data.numero_report,
        numero_fav_time=data.numero_fav_time,
        numero_place_vastu=data.numero_place_vastu,
        numero_fasts=data.numero_fasts_report,
        numero_fav_lord=data.numero_fav_lord,
        numero_fav_mantra=data.numero_fav_mantra,
        numero_daily=data.numero_prediction_daily,
        locale=locale,
        lang=lang,
    )

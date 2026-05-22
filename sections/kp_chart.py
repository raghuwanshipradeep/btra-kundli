from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES, SIGN_NAMES_BY_ID, SIGN_NAMES_HI_BY_ID

if TYPE_CHECKING:
    from models import KundliData


def render_kp_chart(data: KundliData, lang: str = "en") -> str | None:
    if (
        not data.kp_birth_chart
        and not data.kp_planets
        and not data.kp_house_cusps
        and not data.kp_house_significator
        and not data.kp_planet_significator
        and not data.kp_horoscope
    ):
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("kp_chart.html")

    sign_map = SIGN_NAMES_HI_BY_ID if lang == "hi" else SIGN_NAMES_BY_ID

    return template.render(
        kp_houses=data.kp_birth_chart,
        kp_planets=data.kp_planets,
        kp_house_cusps=data.kp_house_cusps,
        kp_house_significator=data.kp_house_significator,
        kp_planet_significator=data.kp_planet_significator,
        kp_horoscope=data.kp_horoscope,
        locale={**locale, "sign_names_by_id": sign_map},
        lang=lang,
    )

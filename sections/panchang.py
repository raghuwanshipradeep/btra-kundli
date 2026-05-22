from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_panchang(data: KundliData, lang: str = "en") -> str | None:
    has_any = (
        data.panchang
        or data.basic_panchang
        or data.basic_panchang_sunrise
        or data.advanced_panchang_sunrise
        or data.planet_panchang
        or data.planet_panchang_sunrise
        or data.chaughadiya_muhurta
        or data.hora_muhurta
        or data.hora_muhurta_dinman
        or data.panchang_chart
        or data.tamil_month_panchang
        or data.tamil_panchang
        or data.panchang_festival
        or data.monthly_panchang
    )
    if not has_any:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("panchang.html")
    return template.render(
        panchang=data.panchang,
        basic_panchang=data.basic_panchang,
        basic_panchang_sunrise=data.basic_panchang_sunrise,
        advanced_panchang_sunrise=data.advanced_panchang_sunrise,
        planet_panchang=data.planet_panchang,
        planet_panchang_sunrise=data.planet_panchang_sunrise,
        chaughadiya_muhurta=data.chaughadiya_muhurta,
        hora_muhurta=data.hora_muhurta,
        hora_muhurta_dinman=data.hora_muhurta_dinman,
        panchang_chart=data.panchang_chart,
        tamil_month_panchang=data.tamil_month_panchang,
        tamil_panchang=data.tamil_panchang,
        panchang_festival=data.panchang_festival,
        monthly_panchang=data.monthly_panchang,
        locale=locale,
        lang=lang,
    )

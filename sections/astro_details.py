from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_astro_details(data: KundliData, lang: str = "en") -> str | None:
    if not data.astro_details and not data.ayanamsha_details:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("astro_details.html")
    return template.render(
        astro=data.astro_details,
        ayanamsha_list=data.ayanamsha_details,
        locale=locale,
        lang=lang,
    )

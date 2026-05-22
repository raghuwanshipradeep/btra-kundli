from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData


def render_astro_details(data: KundliData, lang: str = "en") -> str | None:
    if not data.astro_details and not data.ayanamsha_details:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("astro_details.html")
    return template.render(
        astro=data.astro_details,
        ayanamsha_list=data.ayanamsha_details,
        locale=locale,
        lang=lang,
    )

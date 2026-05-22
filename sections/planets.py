from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData


def render_planets(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("planets_table.html")
    return template.render(
        planets=data.planets,
        narratives=data.narratives,
        locale=locale,
        lang=lang,
    )

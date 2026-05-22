from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData


def render_houses(data: KundliData, lang: str = "en") -> str | None:
    if not data.houses:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("houses_table.html")
    return template.render(
        houses=data.houses,
        locale=locale,
        lang=lang,
    )

from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData


def render_planet_nature(data: KundliData, lang: str = "en") -> str | None:
    if not data.planet_nature:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    planet_names = locale.get("planet_names", {})
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("planet_nature.html")
    return template.render(
        nature=data.planet_nature,
        planet_names=planet_names,
        locale=locale,
        lang=lang,
    )

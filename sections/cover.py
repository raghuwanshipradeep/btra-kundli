from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData


def render_cover(data: KundliData, lang: str = "en") -> str | None:
    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("cover.html")
    return template.render(
        name=data.request.name,
        request=data.request,
        birth=data.birth_details,
        planets=data.planets,
        locale=locale,
        lang=lang,
        generated_date=date.today().strftime("%d %B %Y"),
    )

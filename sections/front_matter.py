from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData


def render_front_matter(data: KundliData, lang: str = "en") -> str | None:
    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("front_matter.html")
    return template.render(
        name=data.request.name,
        locale=locale,
        lang=lang,
    )

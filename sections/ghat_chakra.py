from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData


def render_ghat_chakra(data: KundliData, lang: str = "en") -> str | None:
    if not data.ghat_chakra:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("ghat_chakra.html")
    return template.render(
        ghat=data.ghat_chakra,
        locale=locale,
        lang=lang,
    )

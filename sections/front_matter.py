from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_front_matter(data: KundliData, lang: str = "en") -> str | None:
    """Disclaimer + 'How to Read This Report' pages."""
    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("front_matter.html")
    return template.render(
        name=data.request.name,
        locale=locale,
        lang=lang,
    )


def render_front_matter_toc(data: KundliData, lang: str = "en") -> str | None:
    """Table of Contents page (split out so the cover can sit before it)."""
    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("front_matter_toc.html")
    return template.render(
        name=data.request.name,
        locale=locale,
        lang=lang,
    )

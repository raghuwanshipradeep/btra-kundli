from __future__ import annotations

from typing import TYPE_CHECKING


from branding import brand_for
from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_authors_note(data: KundliData, lang: str = "en") -> str | None:
    brand = brand_for(data)
    if not brand.author_name:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env(brand)
    template = env.get_template("authors_note.html")
    return template.render(
        author_name=brand.author_name,
        author_title=brand.author_title,
        name=data.request.name,
        locale=locale,
        lang=lang,
    )

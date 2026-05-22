from __future__ import annotations

from typing import TYPE_CHECKING


from config import settings
from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_authors_note(data: KundliData, lang: str = "en") -> str | None:
    if not settings.author_name:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("authors_note.html")
    return template.render(
        author_name=settings.author_name,
        author_title=settings.author_title,
        name=data.request.name,
        locale=locale,
        lang=lang,
    )

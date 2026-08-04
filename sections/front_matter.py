from __future__ import annotations

import logging
from typing import TYPE_CHECKING


from sections import LOCALES, TOC_CHAPTERS, make_env

if TYPE_CHECKING:
    from collections.abc import Collection

    from models import KundliData

logger = logging.getLogger(__name__)


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


def build_toc_items(
    lang: str = "en",
    rendered_sections: Collection[str] | None = None,
) -> list[dict[str, str]]:
    """TOC rows, in page order, for chapters that actually produced output.

    `rendered_sections` is the set of section names that returned HTML in this run.
    `None` means "the caller doesn't know" and lists every chapter — that is what
    keeps the plain renderer(data, lang) contract meaningful for previews and tests.
    """
    strings = LOCALES.get(lang, LOCALES["en"]).get("fm_toc_items") or {}
    fallback = LOCALES["en"]["fm_toc_items"]
    items: list[dict[str, str]] = []
    for key, members in TOC_CHAPTERS:
        if rendered_sections is not None and not any(m in rendered_sections for m in members):
            continue
        entry = strings.get(key) or fallback.get(key)
        if not entry:
            # Never print a raw chapter key into a paid PDF; drop the row and shout.
            logger.warning("TOC chapter '%s' has no fm_toc_items entry; row omitted", key)
            continue
        items.append({"name": entry["name"], "desc": entry["desc"]})
    return items


def render_front_matter_toc(
    data: KundliData,
    lang: str = "en",
    rendered_sections: Collection[str] | None = None,
) -> str | None:
    """Table of Contents page (split out so the cover can sit before it).

    Rows are derived from `rendered_sections` so the TOC cannot advertise a chapter
    whose sections produced nothing. PDFGenerator.generate() passes that set after
    the render loop; see DEFERRED_SECTIONS there.
    """
    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("front_matter_toc.html")
    return template.render(
        name=data.request.name,
        locale=locale,
        lang=lang,
        toc_items=build_toc_items(lang, rendered_sections),
    )

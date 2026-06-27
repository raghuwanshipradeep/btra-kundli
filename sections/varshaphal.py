from __future__ import annotations

import logging
from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData

logger = logging.getLogger(__name__)


def render_varshaphal(data: KundliData, lang: str = "en") -> str | None:
    narrative = data.narratives.get("varshaphal", "")
    if not narrative:
        logger.debug("varshaphal: no narrative generated")
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("varshaphal.html")
    return template.render(
        narrative=narrative,
        locale=locale,
        lang=lang,
    )

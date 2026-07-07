from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData

logger = logging.getLogger(__name__)

# Ordered category keys -> locale label keys. "overall" is rendered as a lead
# paragraph; the rest become labeled full-width sub-sections.
_CATEGORY_LABELS = [
    ("career", "varshaphal_career"),
    ("health", "varshaphal_health"),
    ("wealth", "varshaphal_wealth"),
    ("family", "varshaphal_family"),
]


def _parse_structured(raw: str) -> dict | None:
    """Parse the varshaphal JSON narrative; return None if it isn't the structured shape."""
    if not raw:
        return None
    text = raw.strip()
    if not text.startswith("{"):
        return None
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(parsed, dict) and any(
        parsed.get(k) for k in ("overall", "career", "health", "wealth", "family")
    ):
        return parsed
    return None


def render_varshaphal(data: KundliData, lang: str = "en") -> str | None:
    narrative = data.narratives.get("varshaphal", "")
    if not narrative:
        logger.debug("varshaphal: no narrative generated")
        return None

    locale = LOCALES.get(lang, LOCALES["en"])

    overall = ""
    blocks: list[dict[str, str]] = []
    fallback = ""

    parsed = _parse_structured(narrative)
    if parsed:
        overall = (parsed.get("overall") or "").strip()
        for key, label_key in _CATEGORY_LABELS:
            text = (parsed.get(key) or "").strip()
            if text:
                blocks.append({"label": locale.get(label_key, label_key), "text": text})
    else:
        # Old cache / degraded output: render as a plain paragraph.
        fallback = narrative

    env = make_env()
    template = env.get_template("varshaphal.html")
    return template.render(
        overall=overall,
        blocks=blocks,
        fallback=fallback,
        locale=locale,
        lang=lang,
    )

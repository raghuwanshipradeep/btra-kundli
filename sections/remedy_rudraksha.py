from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env
from sections.remedy_constants import RUDRAKSHA_MEANINGS

if TYPE_CHECKING:
    from models import KundliData


def render_remedy_rudraksha(data: KundliData, lang: str = "en") -> str | None:
    if not data.rudraksha_suggestion:
        return None

    raw = data.rudraksha_suggestion
    suggestions = raw.get("rudraksha_suggestion", raw) if isinstance(raw, dict) else raw
    if not isinstance(suggestions, list):
        suggestions = [suggestions] if suggestions else []
    suggestions = suggestions[:3]

    rudraksha_list = []
    for item in suggestions:
        if not isinstance(item, dict):
            continue
        mukhi = item.get("mukhi")
        if mukhi is None:
            continue
        mukhi_int = int(mukhi) if not isinstance(mukhi, int) else mukhi
        meaning = RUDRAKSHA_MEANINGS.get(mukhi_int, {})
        rudraksha_list.append({
            "mukhi": mukhi_int,
            "planet": item.get("planet", meaning.get("planet", "")),
            "benefit": item.get("benefit", meaning.get("benefit", "")),
            "deity": meaning.get("deity", ""),
        })

    if not rudraksha_list:
        return None

    puja_list = []
    if data.puja_suggestion and isinstance(data.puja_suggestion, dict):
        puja_list = data.puja_suggestion.get("puja_list", [])

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("remedy_rudraksha.html")
    return template.render(
        rudraksha_list=rudraksha_list,
        puja_list=puja_list,
        narrative_personal=data.narratives.get("rudraksha_personal", ""),
        narrative_guidance=data.narratives.get("rudraksha_guidance", ""),
        locale=locale,
        lang=lang,
    )

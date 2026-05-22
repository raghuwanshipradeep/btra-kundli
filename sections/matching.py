from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import MatchData


def render_matching(data: MatchData, lang: str = "en") -> str | None:
    has_any = (
        data.match_birth_details
        or data.match_astro_details
        or data.match_ashtakoot_points
        or data.match_dashakoot_points
        or data.match_percentage
        or data.match_report
        or data.match_detailed_report
        or data.match_obstructions
        or data.match_manglik_report
        or data.match_planet_details
    )
    if not has_any:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("matching.html")
    return template.render(
        match=data,
        locale=locale,
        lang=lang,
    )

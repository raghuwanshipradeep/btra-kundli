from __future__ import annotations

import logging
from typing import TYPE_CHECKING


from sections import LOCALES, make_env
from sections.career_path import _get_house_sign
from sections.life_area_remedies import build_area_remedies
from sections.remedy_constants import SIGN_LORDS

if TYPE_CHECKING:
    from models import KundliData

logger = logging.getLogger(__name__)

CAREER_HOUSES = {2, 6, 10}
FINANCE_HOUSES = {2, 5, 8, 11}
RELATIONSHIP_HOUSES = {5, 7, 12}
HEALTH_HOUSES = {1, 6, 8}
SPIRITUAL_HOUSES = {5, 9, 12}


def _build_theme(
    house_reports: dict[str, dict],
    rashi_reports: dict[str, dict],
    target_houses: set[int],
    planets: list,
) -> list[dict]:
    entries = []
    planet_in_houses = {p.name: p.house for p in planets if p.name != "Ascendant"}

    for name, house_num in planet_in_houses.items():
        if house_num not in target_houses:
            continue
        hr = house_reports.get(name, {})
        rr = rashi_reports.get(name, {})
        entry = {"planet": name, "house": house_num}
        if hr.get("report"):
            entry["house_report"] = hr["report"]
        if rr.get("report"):
            entry["rashi_report"] = rr["report"]
        if "house_report" in entry or "rashi_report" in entry:
            entries.append(entry)

    return entries


def render_thematic_reports(data: KundliData, lang: str = "en") -> str | None:
    if not data.general_house_reports or not data.general_rashi_reports or not data.planets:
        logger.debug(
            "thematic_reports: house_reports=%s, rashi_reports=%s, planets=%s",
            bool(data.general_house_reports), bool(data.general_rashi_reports), bool(data.planets),
        )
        return None

    themes = {
        "career": _build_theme(data.general_house_reports, data.general_rashi_reports, CAREER_HOUSES, data.planets),
        "finance": _build_theme(data.general_house_reports, data.general_rashi_reports, FINANCE_HOUSES, data.planets),
        "relationships": _build_theme(data.general_house_reports, data.general_rashi_reports, RELATIONSHIP_HOUSES, data.planets),
        "health": _build_theme(data.general_house_reports, data.general_rashi_reports, HEALTH_HOUSES, data.planets),
        "spiritual": _build_theme(data.general_house_reports, data.general_rashi_reports, SPIRITUAL_HOUSES, data.planets),
    }

    if not any(themes.values()):
        logger.debug("thematic_reports: all theme categories empty (no planet-house report matches)")
        return None

    # Curated remedies for the two domains people most often ask about.
    lagna_lord = SIGN_LORDS.get(_get_house_sign(data.houses, 1), "")
    sixth_lord = SIGN_LORDS.get(_get_house_sign(data.houses, 6), "")
    second_lord = SIGN_LORDS.get(_get_house_sign(data.houses, 2), "")
    eleventh_lord = SIGN_LORDS.get(_get_house_sign(data.houses, 11), "")
    area_remedies = {
        "health": build_area_remedies(data, [lagna_lord, sixth_lord], lang),
        "finance": build_area_remedies(data, [second_lord, eleventh_lord, "Jupiter"], lang),
    }

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("thematic_reports.html")
    return template.render(
        themes=themes,
        area_remedies=area_remedies,
        locale=locale,
        lang=lang,
    )

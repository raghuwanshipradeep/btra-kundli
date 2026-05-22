from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env
from sections.dignity import EXALTATION, OWN_SIGNS, MOOLATRIKONA, DEBILITATION

if TYPE_CHECKING:
    from models import KundliData

VARGA_WEIGHTS = {
    "D1": 3.5, "D2": 1.5, "D3": 1.5, "D4": 1.5, "D5": 1.5,
    "D7": 1.5, "D8": 1.5, "D9": 3.0, "D10": 1.5, "D12": 1.5,
    "D16": 2.0, "D20": 2.0, "D24": 2.0, "D27": 1.5, "D30": 1.0,
    "D40": 1.0, "D45": 1.0, "D60": 4.0,
}


def _score_placement(planet_name: str, sign: str) -> float:
    if EXALTATION.get(planet_name) == sign:
        return 20.0
    if MOOLATRIKONA.get(planet_name) == sign:
        return 15.0
    if sign in OWN_SIGNS.get(planet_name, []):
        return 15.0
    if DEBILITATION.get(planet_name) == sign:
        return 2.0
    return 7.5


def render_shodashvarga_summary(data: KundliData, lang: str = "en") -> str | None:
    if not data.horo_charts and not data.horo_chart_d1:
        return None

    all_charts: dict[str, list] = {}
    if data.horo_chart_d1:
        all_charts["D1"] = data.horo_chart_d1
    if data.horo_charts:
        all_charts.update(data.horo_charts)

    if len(all_charts) < 2:
        return None

    planet_names_list = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    rows = []

    for pname in planet_names_list:
        total_score = 0.0
        chart_count = 0
        for chart_id, signs in all_charts.items():
            weight = VARGA_WEIGHTS.get(chart_id, 1.0)
            for s in signs:
                if pname in s.planet:
                    score = _score_placement(pname, s.sign_name) * weight
                    total_score += score
                    chart_count += 1
                    break

        rows.append({
            "planet": pname,
            "charts_found": chart_count,
            "total_score": round(total_score, 1),
        })

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("shodashvarga_summary.html")
    return template.render(
        summary_rows=rows,
        total_charts=len(all_charts),
        locale=locale,
        lang=lang,
    )

from __future__ import annotations

import logging
from typing import TYPE_CHECKING


from sections import (
    LOCALES,
    SIGN_NAMES_BY_ID,
    SIGN_NAMES_HI_BY_ID,
    PLANET_SHORT_EN,
    PLANET_SHORT_HI,
    TAMIL_TRANSLIT_TO_HI,
    get_north_indian_sign_for_house,
    make_env,
    planet_to_en as _planet_to_en,
)
from sections.north_chart import HOUSE_CENTROIDS
from sections.varga import varga_sign

if TYPE_CHECKING:
    from models import KundliData

logger = logging.getLogger(__name__)

CHART_ORDER = [
    ("D2", "d2_title", "d2_desc"),
    ("D3", "d3_title", "d3_desc"),
    ("D4", "d4_title", "d4_desc"),
    ("D5", "d5_title", "d5_desc"),
    ("D7", "d7_title", "d7_desc"),
    # D8 (Ashtamsa) is omitted: the API's /horo_chart/D8 data is degenerate — it
    # returns contradictory signs for the same sign+part (7 of 9 planets land in
    # Aries with ten signs empty), so no ascendant formula can validate against it.
    # D9 (Navamsa) is shown earlier, embedded in the panchang page right after the
    # D1 lagna chart (classic Rasi+Navamsa pairing) — see sections/panchang.py.
    ("D10", "d10_title", "d10_desc"),
    ("D12", "d12_title", "d12_desc"),
]


def _varga_lagna_sign(data, chart_data, chart_id) -> int | None:
    """Compute the varga ascendant sign (1-12) for one divisional chart.

    The API doesn't return the varga ascendant, so we derive it from the D1
    ascendant longitude with classical formulas (sections/varga.py). To guard
    against ayanamsha/convention mismatches, we self-validate: the same formula
    must reproduce the API's reported varga sign for every planet present
    (>=3 planets, zero mismatches). Otherwise return None → caller falls back.
    """
    try:
        n = int(str(chart_id).lstrip("Dd"))
    except (TypeError, ValueError):
        return None
    if not data or not getattr(data, "planets", None):
        return None

    asc = next(
        (p for p in data.planets if p.name == "Ascendant"),
        next((p for p in data.planets if p.id == 9), None),
    )
    if asc is None or asc.fullDegree is None:
        return None

    # API's varga sign per (English canonical) planet name.
    api_varga: dict[str, int] = {}
    for entry in chart_data:
        for p in entry.planet:
            api_varga[_planet_to_en(p)] = entry.sign

    matches = 0
    for p in data.planets:
        if p.name == "Ascendant" or p.name not in api_varga or p.fullDegree is None:
            continue
        computed = varga_sign(p.fullDegree, n)
        if computed is None:
            return None
        if computed != api_varga[p.name]:
            return None  # formula doesn't match this API's convention
        matches += 1

    if matches < 3:
        return None

    return varga_sign(asc.fullDegree, n)


def build_chart_houses(chart_data, lang, locale, lagna_sign_id):
    """Build a North Indian 12-house layout for one varga chart so it renders as
    HTML (correct Hindi shaping), instead of the broken API SVG image.

    `lagna_sign_id` is the varga ascendant sign (1-12); when falsy, returns None
    and the caller falls back to the API image.
    """
    if not lagna_sign_id:
        return None

    short = PLANET_SHORT_HI if lang == "hi" else PLANET_SHORT_EN

    # Key by sign id (language-independent) rather than sign_name, which the API
    # localizes. Normalize planet labels to English canonical so short forms map
    # correctly in any language.
    sign_planet_map: dict[int, list[str]] = {}
    for entry in chart_data:
        en_planets = [_planet_to_en(p) for p in entry.planet]
        sign_planet_map[entry.sign] = [short.get(p, p) for p in en_planets]

    sign_names_by_id = locale.get("sign_names_by_id", {})
    houses = []
    for h in range(1, 13):
        sid = get_north_indian_sign_for_house(h, lagna_sign_id)
        sign_name_en = SIGN_NAMES_BY_ID[sid]
        cx, cy = HOUSE_CENTROIDS[h]
        houses.append({
            "house": h,
            "sign_id": sid,
            "sign_name": sign_names_by_id.get(sid, sign_name_en),
            "planets": sign_planet_map.get(sid, []),
            "cx": cx,
            "cy": cy,
        })
    return houses


def _fallback_rows(signs_sorted, lang, locale):
    """Flat sign→planets rows, used when the diamond can't be drawn and the API image
    isn't usable. Same naming as build_chart_houses() so the two agree."""
    short = PLANET_SHORT_HI if lang == "hi" else PLANET_SHORT_EN
    sign_names_by_id = locale.get("sign_names_by_id", {})
    rows = []
    for entry in signs_sorted:
        sid = getattr(entry, "sign", None)
        if not sid:
            continue
        en_planets = [_planet_to_en(p) for p in entry.planet]
        rows.append({
            "sign_name": sign_names_by_id.get(sid, SIGN_NAMES_BY_ID.get(sid, str(sid))),
            "planets": [short.get(p, p) for p in en_planets],
        })
    return rows or None


def build_varga_chart(data, chart_data, chart_id, lang, locale):
    """Compute the varga ascendant and build the North Indian house layout, or
    None if the ascendant can't be reliably determined."""
    lagna_sign_id = _varga_lagna_sign(data, chart_data, chart_id)
    return build_chart_houses(chart_data, lang, locale, lagna_sign_id)


def render_divisional_charts(data: KundliData, lang: str = "en") -> str | None:
    if not data.horo_charts:
        logger.debug("divisional_charts: horo_charts is empty/None")
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    images = data.horo_chart_images or {}

    logger.info("divisional_charts: horo_charts keys=%s, images keys=%s",
                list(data.horo_charts.keys()), list(images.keys()))

    charts = []
    for chart_id, title_key, desc_key in CHART_ORDER:
        chart_data = data.horo_charts.get(chart_id)
        if not chart_data:
            continue
        image_url = images.get(chart_id)
        signs_sorted = sorted(chart_data, key=lambda s: s.sign if hasattr(s, 'sign') else 0)
        houses = build_varga_chart(data, chart_data, chart_id, lang, locale)
        # The diamond needs a varga ascendant we can trust; _varga_lagna_sign() returns
        # None when our formula can't reproduce this API's own placements. In Hindi the
        # API's inline SVG is no use either (unshapeable Devanagari in WeasyPrint), so
        # drop it and let the template's sign→planet table carry the data.
        if houses is None and lang == "hi" and isinstance(image_url, str) \
                and image_url.startswith("data:image/svg+xml"):
            image_url = None
        rows = None
        if houses is None and not image_url:
            rows = _fallback_rows(signs_sorted, lang, locale)
        logger.info("divisional_charts: %s → %d signs, houses=%s, image=%s, table=%s",
                    chart_id, len(signs_sorted), "yes" if houses else "no",
                    "yes" if image_url else "no", "yes" if rows else "no")
        charts.append({
            "id": chart_id,
            "title": locale.get(title_key, chart_id),
            "desc": locale.get(desc_key, ""),
            "signs": signs_sorted,
            "houses": houses,
            "image_url": image_url,
            "rows": rows,
        })

    if not charts:
        return None

    logger.info("divisional_charts: rendering %d charts (%s)",
                len(charts), ", ".join(c["id"] for c in charts))

    env = make_env()
    template = env.get_template("divisional_charts.html")
    return template.render(
        charts=charts,
        sign_names_hi=SIGN_NAMES_HI_BY_ID,
        locale=locale,
        lang=lang,
    )

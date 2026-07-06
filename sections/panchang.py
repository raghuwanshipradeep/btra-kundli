from __future__ import annotations

import copy
import logging
import math
from typing import TYPE_CHECKING


from sections import LOCALES, make_env, planet_to_en
from sections.north_chart import build_lagna_houses
from sections.divisional_charts import build_varga_chart

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from models import KundliData


def _sanitize_nan(obj):
    """Recursively replace NaN-like strings and values with None."""
    if isinstance(obj, dict):
        return {k: _sanitize_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_nan(v) for v in obj]
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, str) and "nan" in obj.lower():
        return None
    return obj


def _hours_to_hms(hours):
    """Convert decimal hours (e.g. 6.50) to HH:MM format."""
    if hours is None or not isinstance(hours, (int, float)):
        return "—"
    if isinstance(hours, float) and math.isnan(hours):
        return "—"
    total_minutes = round(hours * 60)
    h = total_minutes // 60
    m = total_minutes % 60
    return f"{h:02d}:{m:02d}"


def _empty_to_none(obj):
    """Convert empty dicts/lists to None so Jinja truthiness skips them."""
    if isinstance(obj, dict) and len(obj) == 0:
        return None
    if isinstance(obj, list) and len(obj) == 0:
        return None
    return obj


# The real API omits the chaughadiya "type" (nature), so the प्रकार column comes up
# blank. Each chaughadiya's nature is fixed by its name, so derive it. Keyed by both
# English and Hindi names (lowercased; Devanagari has no case so it's a no-op there).
_CHAUGHADIYA_NATURE = {
    "amrit": "auspicious", "अमृत": "auspicious",
    "shubh": "auspicious", "शुभ": "auspicious",
    "labh": "auspicious", "लाभ": "auspicious",
    "char": "neutral", "chal": "neutral", "चर": "neutral", "चल": "neutral",
    "rog": "inauspicious", "रोग": "inauspicious",
    "kaal": "inauspicious", "kal": "inauspicious", "काल": "inauspicious",
    "udveg": "inauspicious", "उद्वेग": "inauspicious",
}
_NATURE_LABELS = {
    "en": {"auspicious": "Auspicious", "neutral": "Neutral", "inauspicious": "Inauspicious"},
    "hi": {"auspicious": "शुभ", "neutral": "सम", "inauspicious": "अशुभ"},
}


def _fill_planet_panchang_degrees(pp, planets):
    """Fill the अंश (degree) column from data.planets (authoritative normDegree) when
    the real API omits it. planet_panchang positions equal the birth chart, so the
    degree is matched by (normalized) planet name. Existing values are not overridden."""
    if not planets or not pp:
        return
    deg_by = {p.name: p.normDegree for p in planets}   # English canonical names
    items = pp.get("planets") if isinstance(pp, dict) and "planets" in pp else pp
    if not isinstance(items, list):
        return
    for it in items:
        if isinstance(it, dict) and not it.get("degree") and not it.get("norm_degree"):
            name_en = planet_to_en(str(it.get("planet") or it.get("name") or ""))
            deg = deg_by.get(name_en)
            if deg is not None:
                it["degree"] = f"{deg:.2f}°"


def _fill_chaughadiya_type(obj, labels):
    """Recursively set item['type'] from the chaughadiya name where the API left it
    empty. Non-chaughadiya dicts map to None and are left untouched."""
    if isinstance(obj, list):
        for it in obj:
            _fill_chaughadiya_type(it, labels)
    elif isinstance(obj, dict):
        if not obj.get("type") and not obj.get("is_day"):
            name = str(obj.get("muhurta") or obj.get("name") or "").strip().lower()
            nature = _CHAUGHADIYA_NATURE.get(name)
            if nature:
                obj["type"] = labels[nature]
        for v in obj.values():
            _fill_chaughadiya_type(v, labels)


def render_panchang(data: KundliData, lang: str = "en") -> str | None:
    has_any = (
        data.panchang
        or data.basic_panchang
        or data.basic_panchang_sunrise
        or data.advanced_panchang_sunrise
        or data.planet_panchang
        or data.planet_panchang_sunrise
        or data.chaughadiya_muhurta
        or data.hora_muhurta
    )
    if not has_any:
        return None

    logger.info(
        "Panchang data: chaughadiya=%s hora=%s",
        type(data.chaughadiya_muhurta).__name__ if data.chaughadiya_muhurta else None,
        type(data.hora_muhurta).__name__ if data.hora_muhurta else None,
    )

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("panchang.html")
    birth_ayan = 0.0
    if data.birth_details:
        birth_ayan = data.birth_details.ayanamsha

    # Chaughadiya: derive the missing प्रकार (type) from each muhurta's name.
    chaughadiya = _empty_to_none(_sanitize_nan(data.chaughadiya_muhurta))
    _fill_chaughadiya_type(chaughadiya, _NATURE_LABELS.get(lang, _NATURE_LABELS["en"]))

    # Graha Panchang: fill the अंश (degree) column from data.planets when the API omits it.
    planet_pp = copy.deepcopy(data.planet_panchang) if data.planet_panchang else data.planet_panchang
    _fill_planet_panchang_degrees(planet_pp, data.planets)

    # Navamsa (D9) chart, shown right after the D1 lagna chart (classic Rasi+Navamsa
    # pairing). Uses the same varga builder as the divisional-charts section.
    navamsa_houses = None
    navamsa_image = None
    if data.horo_charts and data.horo_charts.get("D9"):
        d9_data = data.horo_charts.get("D9")
        navamsa_houses = build_varga_chart(data, d9_data, "D9", lang, locale)
        navamsa_image = (data.horo_chart_images or {}).get("D9")
        # Drop the API's unshapeable inline SVG for Hindi (garbled Devanagari).
        if navamsa_houses is None and lang == "hi" and isinstance(navamsa_image, str) \
                and navamsa_image.startswith("data:image/svg+xml"):
            navamsa_image = None

    return template.render(
        panchang=data.panchang,
        lagna_houses=build_lagna_houses(data, lang, locale, with_details=True),
        navamsa_houses=navamsa_houses,
        navamsa_image=navamsa_image,
        navamsa_title=locale.get("d9_title", "Navamsa (D9)"),
        navamsa_desc=locale.get("d9_desc", ""),
        birth_ayanamsha=birth_ayan,
        basic_panchang=_sanitize_nan(data.basic_panchang),
        basic_panchang_sunrise=_sanitize_nan(data.basic_panchang_sunrise),
        advanced_panchang_sunrise=_sanitize_nan(data.advanced_panchang_sunrise),
        planet_panchang=planet_pp,
        planet_panchang_sunrise=data.planet_panchang_sunrise,
        chaughadiya_muhurta=chaughadiya,
        hora_muhurta=_empty_to_none(_sanitize_nan(data.hora_muhurta)),
        locale=locale,
        lang=lang,
    )

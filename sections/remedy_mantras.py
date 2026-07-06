from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env
from sections.remedy_constants import (
    PLANET_MANTRAS,
    PLANET_MANTRAS_DEVANAGARI,
    PLANET_MANTRAS_MEANING,
    SIGN_LORDS,
    TWELFTH_LORD_ISHTADEVATA,
    DEITY_HI,
    SHLOKA_HI,
)

if TYPE_CHECKING:
    from models import KundliData


def _get_house_lord(houses, house_num: int) -> str:
    if not houses:
        return ""
    for h in houses:
        hid = getattr(h, "house_id", None) or getattr(h, "house", 0)
        if isinstance(h, dict):
            hid = h.get("house_id", h.get("house", 0))
        if hid == house_num:
            sign = getattr(h, "sign", "") or (h.get("sign", "") if isinstance(h, dict) else "")
            lord = getattr(h, "sign_lord", "") or SIGN_LORDS.get(sign, "")
            if isinstance(h, dict) and not lord:
                lord = h.get("sign_lord", SIGN_LORDS.get(sign, ""))
            return lord
    return ""


def render_remedy_mantras(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    planet_names = [p.name for p in data.planets if p.name != "Ascendant"]

    mantra_rows = []
    for pname in planet_names:
        if pname not in PLANET_MANTRAS:
            continue
        info = PLANET_MANTRAS[pname]
        deity = info["deity"]
        mantra_rows.append({
            "planet": pname,
            "devanagari": PLANET_MANTRAS_DEVANAGARI.get(pname, ""),
            "transliteration": info["mantra"],
            "meaning": PLANET_MANTRAS_MEANING.get(pname, ""),
            "count": info["count"],
            "deity": DEITY_HI.get(deity, deity) if lang == "hi" else deity,
        })

    twelfth_lord = _get_house_lord(data.houses, 12)
    ishta_info = TWELFTH_LORD_ISHTADEVATA.get(twelfth_lord, {})
    ishta_devata = ishta_info.get("deity", "")
    ishta_shloka = ishta_info.get("shloka", "")
    if lang == "hi":
        ishta_devata = DEITY_HI.get(ishta_devata, ishta_devata)
        ishta_shloka = SHLOKA_HI.get(ishta_shloka, ishta_shloka)

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("remedy_mantras.html")
    return template.render(
        mantra_rows=mantra_rows,
        ishta_devata=ishta_devata,
        ishta_shloka=ishta_shloka,
        twelfth_lord=twelfth_lord,
        narrative=data.narratives.get("mantra_guidance", ""),
        locale=locale,
        lang=lang,
    )

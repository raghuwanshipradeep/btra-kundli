from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES
from sections.remedy_constants import (
    PLANET_MANTRAS,
    PLANET_MANTRAS_DEVANAGARI,
    PLANET_MANTRAS_MEANING,
    SIGN_LORDS,
    TWELFTH_LORD_ISHTADEVATA,
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
        mantra_rows.append({
            "planet": pname,
            "devanagari": PLANET_MANTRAS_DEVANAGARI.get(pname, ""),
            "transliteration": info["mantra"],
            "meaning": PLANET_MANTRAS_MEANING.get(pname, ""),
            "count": info["count"],
            "deity": info["deity"],
        })

    twelfth_lord = _get_house_lord(data.houses, 12)
    ishta_info = TWELFTH_LORD_ISHTADEVATA.get(twelfth_lord, {})
    ishta_devata = ishta_info.get("deity", "")
    ishta_shloka = ishta_info.get("shloka", "")

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
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

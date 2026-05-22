from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env
from sections.remedy_constants import PLANET_TO_GEMSTONE, SIGN_LORDS

if TYPE_CHECKING:
    from models import KundliData


def _compute_atmakaraka(planets: list) -> str | None:
    candidates = [p for p in planets if p.name in {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"}]
    if len(candidates) < 7:
        return None
    best = None
    best_deg = -1.0
    for p in candidates:
        deg = (30.0 - p.normDegree) if p.name == "Rahu" else p.normDegree
        if deg > best_deg:
            best_deg = deg
            best = p.name
    return best


def _get_house_sign_lord(houses, house_num: int) -> tuple[str, str]:
    if not houses:
        return "", ""
    for h in houses:
        hid = getattr(h, "house_id", None) or getattr(h, "house", 0)
        if isinstance(h, dict):
            hid = h.get("house_id", h.get("house", 0))
        if hid == house_num:
            sign = getattr(h, "sign", "") or (h.get("sign", "") if isinstance(h, dict) else "")
            lord = getattr(h, "sign_lord", "") or SIGN_LORDS.get(sign, "")
            if isinstance(h, dict) and not lord:
                lord = h.get("sign_lord", SIGN_LORDS.get(sign, ""))
            return sign, lord
    return "", ""


def render_remedy_gemstones(data: KundliData, lang: str = "en") -> str | None:
    if not data.basic_gem_suggestion:
        return None

    gems = data.basic_gem_suggestion
    api_stones = {
        "life_stone": gems.get("life_stone", {}),
        "lucky_stone": gems.get("lucky_stone", {}),
        "fortune_stone": gems.get("fortune_stone", {}),
    }

    _, lagna_lord = _get_house_sign_lord(data.houses, 1)
    _, ninth_lord = _get_house_sign_lord(data.houses, 9)
    ak_planet = _compute_atmakaraka(data.planets) if data.planets else None

    gem_cards = []

    life = api_stones["life_stone"]
    if life:
        derived = PLANET_TO_GEMSTONE.get(lagna_lord, {})
        gem_cards.append({
            "type": "life_stone",
            "label_key": "rg_jivan_ratna",
            "desc_key": "rg_jivan_desc",
            "name": life.get("name", derived.get("name", "")),
            "hindi_name": derived.get("hindi", ""),
            "planet": life.get("planet", lagna_lord),
            "weight": life.get("weight", ""),
            "metal": life.get("metal", ""),
            "narrative": data.narratives.get("gemstone_life_stone", ""),
        })

    if ak_planet:
        derived_ak = PLANET_TO_GEMSTONE.get(ak_planet, {})
        lucky = api_stones["lucky_stone"]
        gem_cards.append({
            "type": "lucky_stone",
            "label_key": "rg_karaka_ratna",
            "desc_key": "rg_karaka_desc",
            "name": lucky.get("name", derived_ak.get("name", "")) if lucky else derived_ak.get("name", ""),
            "hindi_name": derived_ak.get("hindi", ""),
            "planet": lucky.get("planet", ak_planet) if lucky else ak_planet,
            "weight": lucky.get("weight", "") if lucky else "",
            "metal": lucky.get("metal", "") if lucky else "",
            "narrative": data.narratives.get("gemstone_lucky_stone", ""),
        })

    fortune = api_stones["fortune_stone"]
    if fortune:
        derived_9 = PLANET_TO_GEMSTONE.get(ninth_lord, {})
        gem_cards.append({
            "type": "fortune_stone",
            "label_key": "rg_bhagya_ratna",
            "desc_key": "rg_bhagya_desc",
            "name": fortune.get("name", derived_9.get("name", "")),
            "hindi_name": derived_9.get("hindi", ""),
            "planet": fortune.get("planet", ninth_lord),
            "weight": fortune.get("weight", ""),
            "metal": fortune.get("metal", ""),
            "narrative": data.narratives.get("gemstone_fortune_stone", ""),
        })

    if not gem_cards:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("remedy_gemstones.html")
    return template.render(
        gem_cards=gem_cards,
        locale=locale,
        lang=lang,
    )

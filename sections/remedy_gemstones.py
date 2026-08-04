from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env, planet_to_en
from sections.remedy_constants import PLANET_TO_GEMSTONE, SIGN_LORDS

if TYPE_CHECKING:
    from models import KundliData


def _gem_card(
    api_stone,
    derived_planet: str | None,
    *,
    type_: str,
    label_key: str,
    desc_key: str,
    narrative: str,
) -> dict | None:
    """Build one gemstone card from the API stone, falling back to the derived planet.

    Two things this fixes. (1) The Hindi name now follows the planet actually shown:
    it used to come from the locally derived planet while the English name came from the
    API, so when the two disagreed the Devanagari label named a different stone — and in
    Hindi PDFs the Devanagari is the primary label. (2) A card is emitted whenever
    *either* source can name a stone; previously life_stone and fortune_stone were gated
    on the API alone, so when it returned only lucky_stone the page still claimed
    "three key stones" but printed one.
    """
    api_stone = api_stone if isinstance(api_stone, dict) else {}
    planet = planet_to_en(api_stone.get("planet") or "") or (derived_planet or "")
    entry = PLANET_TO_GEMSTONE.get(planet, {})
    name = api_stone.get("name") or entry.get("name", "")
    if not name:
        return None
    return {
        "type": type_,
        "label_key": label_key,
        "desc_key": desc_key,
        "name": name,
        "hindi_name": entry.get("hindi", ""),
        "planet": planet,
        "weight": api_stone.get("weight", ""),
        "metal": api_stone.get("metal", ""),
        "narrative": narrative,
    }


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

    candidates = [
        _gem_card(
            api_stones["life_stone"], lagna_lord,
            type_="life_stone", label_key="rg_jivan_ratna", desc_key="rg_jivan_desc",
            narrative=data.narratives.get("gemstone_life_stone", ""),
        ),
        _gem_card(
            api_stones["lucky_stone"], ak_planet,
            type_="lucky_stone", label_key="rg_karaka_ratna", desc_key="rg_karaka_desc",
            narrative=data.narratives.get("gemstone_lucky_stone", ""),
        ),
        _gem_card(
            api_stones["fortune_stone"], ninth_lord,
            type_="fortune_stone", label_key="rg_bhagya_ratna", desc_key="rg_bhagya_desc",
            narrative=data.narratives.get("gemstone_fortune_stone", ""),
        ),
    ]
    gem_cards = [c for c in candidates if c]

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

from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env
from sections.remedy_constants import (
    SIGN_LORDS,
    SIGN_TO_ISHTADEVATA,
    TWELFTH_LORD_ISHTADEVATA,
    DEITY_HI,
    SHLOKA_HI,
)

if TYPE_CHECKING:
    from models import KundliData


def _get_house_info(houses, house_num: int) -> tuple[str, str]:
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


def render_remedy_ishta_devata(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets or not data.houses:
        return None

    twelfth_sign, twelfth_lord = _get_house_info(data.houses, 12)
    if not twelfth_lord:
        return None

    ishta_info = TWELFTH_LORD_ISHTADEVATA.get(twelfth_lord, {})
    deity = ishta_info.get("deity", "")
    shloka = ishta_info.get("shloka", "")

    if not deity:
        return None

    moon = next((p for p in data.planets if p.name == "Moon"), None)
    moon_sign = moon.sign if moon else ""
    moon_deity = SIGN_TO_ISHTADEVATA.get(moon_sign, "")

    if lang == "hi":
        deity = DEITY_HI.get(deity, deity)
        moon_deity = DEITY_HI.get(moon_deity, moon_deity)
        shloka = SHLOKA_HI.get(shloka, shloka)

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("remedy_ishta_devata.html")
    return template.render(
        deity=deity,
        shloka=shloka,
        twelfth_sign=twelfth_sign,
        twelfth_lord=twelfth_lord,
        moon_sign=moon_sign,
        moon_deity=moon_deity,
        narrative=data.narratives.get("ishta_devata", ""),
        locale=locale,
        lang=lang,
    )

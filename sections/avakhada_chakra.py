from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_avakhada_chakra(data: KundliData, lang: str = "en") -> str | None:
    if not data.astro_details and not data.birth_details:
        return None

    rows = []
    ad = data.astro_details
    if ad:
        rows.extend([
            ("Varna", ad.Varna),
            ("Vashya", ad.Vashya),
            ("Yoni", ad.Yoni),
            ("Gan", ad.Gan),
            ("Nadi", ad.Nadi),
            ("Nakshatra", ad.Naksahtra),
            ("Nakshatra Lord", ad.NaksahtraLord),
            ("Charan", str(ad.Charan)),
            ("Yoga", ad.Yog),
            ("Karana", ad.Karan),
            ("Tithi", ad.Tithi),
            ("Yunja", ad.yunja),
            ("Tatva", ad.tatva),
            ("Name Alphabet", ad.name_alphabet),
            ("Paya", ad.paya),
            ("Sign", ad.sign),
            ("Sign Lord", ad.SignLord),
            ("Ascendant", ad.ascendant),
            ("Ascendant Lord", ad.ascendant_lord),
        ])

    if data.birth_details:
        bd = data.birth_details
        rows.extend([
            ("Sunrise", bd.sunrise),
            ("Sunset", bd.sunset),
            ("Ayanamsha", f"{bd.ayanamsha:.4f}"),
        ])

    rows = [(k, v) for k, v in rows if v]

    if not rows:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("avakhada_chakra.html")
    return template.render(
        chakra_rows=rows,
        locale=locale,
        lang=lang,
    )

from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, _safe_time, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_avakhada_chakra(data: KundliData, lang: str = "en") -> str | None:
    if not data.astro_details and not data.birth_details:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])

    _LABELS = {
        "en": {
            "varna": "Varna", "vashya": "Vashya", "yoni": "Yoni",
            "gan": "Gan", "nadi": "Nadi", "nakshatra": "Nakshatra",
            "nakshatra_lord": "Nakshatra Lord", "charan": "Charan",
            "yoga": "Yoga", "karana": "Karana", "tithi": "Tithi",
            "yunja": "Yunja", "tatva": "Tatva", "name_alphabet": "Name Alphabet",
            "paya": "Paya", "sign": "Sign", "sign_lord": "Sign Lord",
            "ascendant": "Ascendant", "ascendant_lord": "Ascendant Lord",
            "sunrise": "Sunrise", "sunset": "Sunset", "ayanamsha": "Ayanamsha",
        },
        "hi": {
            "varna": "वर्ण", "vashya": "वश्य", "yoni": "योनि",
            "gan": "गण", "nadi": "नाड़ी", "nakshatra": "नक्षत्र",
            "nakshatra_lord": "नक्षत्र स्वामी", "charan": "चरण",
            "yoga": "योग", "karana": "करण", "tithi": "तिथि",
            "yunja": "युंजा", "tatva": "तत्व", "name_alphabet": "नाम का अक्षर",
            "paya": "पाया", "sign": "राशि", "sign_lord": "राशि स्वामी",
            "ascendant": "लग्न", "ascendant_lord": "लग्न स्वामी",
            "sunrise": "सूर्योदय", "sunset": "सूर्यास्त", "ayanamsha": "अयनांश",
        },
    }
    L = _LABELS.get(lang, _LABELS["en"])

    rows = []
    ad = data.astro_details
    if ad:
        rows.extend([
            (L["varna"], ad.Varna),
            (L["vashya"], ad.Vashya),
            (L["yoni"], ad.Yoni),
            (L["gan"], ad.Gan),
            (L["nadi"], ad.Nadi),
            (L["nakshatra"], ad.Naksahtra),
            (L["nakshatra_lord"], ad.NaksahtraLord),
            (L["charan"], str(ad.Charan)),
            (L["yoga"], ad.Yog),
            (L["karana"], ad.Karan),
            (L["tithi"], ad.Tithi),
            (L["yunja"], ad.yunja),
            (L["tatva"], ad.tatva),
            (L["name_alphabet"], ad.name_alphabet),
            (L["paya"], ad.paya),
            (L["sign"], ad.sign),
            (L["sign_lord"], ad.SignLord),
            (L["ascendant"], ad.ascendant),
            (L["ascendant_lord"], ad.ascendant_lord),
        ])

    if data.birth_details:
        bd = data.birth_details
        rows.extend([
            (L["sunrise"], _safe_time(bd.sunrise)),
            (L["sunset"], _safe_time(bd.sunset)),
            (L["ayanamsha"], f"{bd.ayanamsha:.4f}"),
        ])

    rows = [(k, v) for k, v in rows if v]

    if not rows:
        return None

    env = make_env()
    template = env.get_template("avakhada_chakra.html")
    return template.render(
        chakra_rows=rows,
        locale=locale,
        lang=lang,
    )

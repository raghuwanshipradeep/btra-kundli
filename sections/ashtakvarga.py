from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, SIGN_ORDER_EN, make_env

if TYPE_CHECKING:
    from models import KundliData

PLANET_KEYS = [
    ("sun_points", "Sun"),
    ("moon_points", "Moon"),
    ("mars_points", "Mars"),
    ("mercury_points", "Mercury"),
    ("jupiter_points", "Jupiter"),
    ("venus_points", "Venus"),
    ("saturn_points", "Saturn"),
    ("ascendant_points", "Ascendant"),
]


def render_ashtakvarga(data: KundliData, lang: str = "en") -> str | None:
    if not data.sarvashtak:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("ashtakvarga.html")

    planet_rows = [
        (key, locale["planet_names"].get(label, label)) for key, label in PLANET_KEYS
    ]

    planet_totals: dict[str, int] = {}
    for key, _ in PLANET_KEYS:
        planet_totals[key] = sum(
            getattr(s, key, 0) for s in data.sarvashtak
        )

    grand_total = sum(s.total_points for s in data.sarvashtak)

    sign_order = [
        locale["sign_names"].get(s, s) for s in SIGN_ORDER_EN
    ]

    return template.render(
        sarvashtak=data.sarvashtak,
        planet_rows=planet_rows,
        planet_totals=planet_totals,
        grand_total=grand_total,
        sign_order=sign_order,
        locale=locale,
        lang=lang,
    )

from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData

NAISARGIK_FRIENDS: dict[str, dict[str, str]] = {
    "Sun": {"Moon": "Friend", "Mars": "Friend", "Mercury": "Enemy", "Jupiter": "Friend", "Venus": "Enemy", "Saturn": "Enemy"},
    "Moon": {"Sun": "Friend", "Mars": "Neutral", "Mercury": "Friend", "Jupiter": "Neutral", "Venus": "Neutral", "Saturn": "Neutral"},
    "Mars": {"Sun": "Friend", "Moon": "Friend", "Mercury": "Enemy", "Jupiter": "Friend", "Venus": "Neutral", "Saturn": "Neutral"},
    "Mercury": {"Sun": "Friend", "Moon": "Enemy", "Mars": "Neutral", "Jupiter": "Neutral", "Venus": "Friend", "Saturn": "Neutral"},
    "Jupiter": {"Sun": "Friend", "Moon": "Friend", "Mars": "Friend", "Mercury": "Neutral", "Venus": "Enemy", "Saturn": "Neutral"},
    "Venus": {"Sun": "Enemy", "Moon": "Neutral", "Mars": "Neutral", "Mercury": "Friend", "Jupiter": "Neutral", "Saturn": "Friend"},
    "Saturn": {"Sun": "Enemy", "Moon": "Enemy", "Mars": "Neutral", "Mercury": "Friend", "Jupiter": "Neutral", "Venus": "Friend"},
}

TEMP_FRIEND_OFFSETS = {1, 2, 3, 9, 10, 11}


def _compute_tatkalik(planets: list) -> dict[str, dict[str, str]]:
    ph = {p.name: p.house for p in planets if p.name not in ("Ascendant", "Rahu", "Ketu")}
    planet_names = [n for n in ph]

    result: dict[str, dict[str, str]] = {}
    for p1 in planet_names:
        result[p1] = {}
        for p2 in planet_names:
            if p1 == p2:
                continue
            offset = ((ph[p2] - ph[p1]) % 12)
            if offset in TEMP_FRIEND_OFFSETS:
                result[p1][p2] = "Temp Friend"
            else:
                result[p1][p2] = "Temp Enemy"
    return result


def _compute_compound(naisargik: dict, tatkalik: dict) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for p1 in naisargik:
        result[p1] = {}
        for p2 in naisargik.get(p1, {}):
            n = naisargik[p1][p2]
            t = tatkalik.get(p1, {}).get(p2, "Temp Enemy")

            if n == "Friend" and t == "Temp Friend":
                result[p1][p2] = "Best Friend"
            elif n == "Enemy" and t == "Temp Enemy":
                result[p1][p2] = "Bitter Enemy"
            elif (n == "Friend" and t == "Temp Enemy") or (n == "Enemy" and t == "Temp Friend"):
                result[p1][p2] = "Neutral"
            elif n == "Neutral" and t == "Temp Friend":
                result[p1][p2] = "Friend"
            elif n == "Neutral" and t == "Temp Enemy":
                result[p1][p2] = "Enemy"
            else:
                result[p1][p2] = "Neutral"
    return result


def render_tatkalik_maitri(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    tatkalik = _compute_tatkalik(data.planets)
    compound = _compute_compound(NAISARGIK_FRIENDS, tatkalik)

    planet_order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("tatkalik_maitri.html")
    return template.render(
        tatkalik=tatkalik,
        compound=compound,
        planet_order=planet_order,
        locale=locale,
        lang=lang,
    )

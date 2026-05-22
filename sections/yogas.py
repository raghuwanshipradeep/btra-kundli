from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData

KENDRA_HOUSES = {1, 4, 7, 10}
TRIKONA_HOUSES = {1, 5, 9}


def _planet_house_map(planets: list) -> dict[str, int]:
    return {p.name: p.house for p in planets if p.name != "Ascendant"}


def _planet_sign_map(planets: list) -> dict[str, str]:
    return {p.name: p.sign for p in planets if p.name != "Ascendant"}


def _houses_from_ref(ref_house: int, offset: int) -> int:
    return ((ref_house - 1 + offset) % 12) + 1


def _detect_yogas(planets: list, houses: list | None) -> list[dict]:
    ph = _planet_house_map(planets)
    ps = _planet_sign_map(planets)
    found: list[dict] = []

    sun_h = ph.get("Sun")
    merc_h = ph.get("Mercury")
    if sun_h is not None and sun_h == merc_h:
        found.append({
            "name": "Budh-Aditya Yoga",
            "planets": "Sun + Mercury",
            "house": sun_h,
            "description": "Sun and Mercury together bestow intelligence, eloquence, and analytical abilities.",
            "effect": "Benefic",
        })

    moon_h = ph.get("Moon")
    jup_h = ph.get("Jupiter")
    if moon_h and jup_h:
        offset = ((jup_h - moon_h) % 12)
        if offset in (0, 3, 6, 9):
            found.append({
                "name": "Gajakesari Yoga",
                "planets": "Moon + Jupiter",
                "house": f"Moon H{moon_h}, Jupiter H{jup_h}",
                "description": "Jupiter in kendra from Moon grants fame, wealth, and wisdom.",
                "effect": "Highly Benefic",
            })

    mars_h = ph.get("Mars")
    venus_h = ph.get("Venus")
    sat_h = ph.get("Saturn")

    for planet, sign in ps.items():
        p_house = ph.get(planet)
        if planet == "Mars" and sign in ("Aries", "Scorpio", "Capricorn") and p_house in KENDRA_HOUSES:
            found.append({
                "name": "Ruchaka Yoga",
                "planets": "Mars",
                "house": p_house,
                "description": "Mars in own/exalted sign in kendra gives courage, leadership, and physical strength.",
                "effect": "Panch Mahapurusha",
            })
        if planet == "Mercury" and sign in ("Gemini", "Virgo") and p_house in KENDRA_HOUSES:
            found.append({
                "name": "Bhadra Yoga",
                "planets": "Mercury",
                "house": p_house,
                "description": "Mercury in own/exalted sign in kendra gives intelligence and communication skills.",
                "effect": "Panch Mahapurusha",
            })
        if planet == "Jupiter" and sign in ("Sagittarius", "Pisces", "Cancer") and p_house in KENDRA_HOUSES:
            found.append({
                "name": "Hamsa Yoga",
                "planets": "Jupiter",
                "house": p_house,
                "description": "Jupiter in own/exalted sign in kendra gives wisdom, spirituality, and good fortune.",
                "effect": "Panch Mahapurusha",
            })
        if planet == "Venus" and sign in ("Taurus", "Libra", "Pisces") and p_house in KENDRA_HOUSES:
            found.append({
                "name": "Malavya Yoga",
                "planets": "Venus",
                "house": p_house,
                "description": "Venus in own/exalted sign in kendra gives luxury, beauty, and artistic talents.",
                "effect": "Panch Mahapurusha",
            })
        if planet == "Saturn" and sign in ("Capricorn", "Aquarius", "Libra") and p_house in KENDRA_HOUSES:
            found.append({
                "name": "Shasha Yoga",
                "planets": "Saturn",
                "house": p_house,
                "description": "Saturn in own/exalted sign in kendra gives authority, discipline, and longevity.",
                "effect": "Panch Mahapurusha",
            })

    if venus_h is not None and venus_h == merc_h:
        found.append({
            "name": "Lakshmi Yoga",
            "planets": "Venus + Mercury",
            "house": venus_h,
            "description": "Conjunction of Venus and Mercury indicates wealth and artistic talent.",
            "effect": "Benefic",
        })

    if moon_h:
        h2 = _houses_from_ref(moon_h, 1)
        h12 = _houses_from_ref(moon_h, -1)
        benefics_adjacent = [
            n for n in ("Jupiter", "Venus", "Mercury")
            if ph.get(n) in (h2, h12)
        ]
        if len(benefics_adjacent) >= 2:
            found.append({
                "name": "Sunapha Yoga" if all(ph.get(n) == h2 for n in benefics_adjacent) else "Anapha/Durudhara Yoga",
                "planets": ", ".join(benefics_adjacent),
                "house": f"Near Moon H{moon_h}",
                "description": "Benefic planets flanking Moon bestow wealth, intelligence, and good fortune.",
                "effect": "Benefic",
            })

    rahu_h = ph.get("Rahu")
    if rahu_h is not None and rahu_h == mars_h and rahu_h in (1, 5, 9):
        found.append({
            "name": "Angarak Yoga",
            "planets": "Mars + Rahu",
            "house": mars_h,
            "description": "Mars-Rahu conjunction in trikona can cause aggression but also fearlessness.",
            "effect": "Mixed",
        })

    if houses:
        h9 = next((h for h in houses if h.house_id == 9), None)
        h10 = next((h for h in houses if h.house_id == 10), None)
        if h9 and h10:
            lord9 = h9.sign_lord
            lord10 = h10.sign_lord
            if ph.get(lord9) == ph.get(lord10) and lord9 != lord10:
                found.append({
                    "name": "Dharma-Karmadhipati Yoga",
                    "planets": f"{lord9} + {lord10}",
                    "house": ph.get(lord9, 0),
                    "description": "Lords of 9th and 10th house conjunct. Exceptional career success through righteous actions.",
                    "effect": "Highly Benefic",
                })

    benefic_set = {"Jupiter", "Venus", "Mercury", "Moon"}
    for h in KENDRA_HOUSES:
        planets_in_kendra = [n for n, hh in ph.items() if hh == h and n in benefic_set]
        if len(planets_in_kendra) >= 2:
            found.append({
                "name": "Chandra-Mangal Yoga" if "Moon" in planets_in_kendra and "Mars" in [n for n, hh in ph.items() if hh == h] else "Subha Kartari Yoga",
                "planets": ", ".join(planets_in_kendra),
                "house": h,
                "description": "Multiple benefic planets in a kendra house strengthen that area of life.",
                "effect": "Benefic",
            })
            break

    if moon_h is not None and moon_h == mars_h:
        found.append({
            "name": "Chandra-Mangal Yoga",
            "planets": "Moon + Mars",
            "house": moon_h,
            "description": "Moon-Mars conjunction gives wealth through self-effort and courage.",
            "effect": "Benefic",
        })

    # Vesi Yoga: non-Moon planet in 2nd from Sun
    if sun_h is not None:
        h2_from_sun = _houses_from_ref(sun_h, 1)
        h12_from_sun = _houses_from_ref(sun_h, -1)
        vesi_planets = [n for n in ("Mercury", "Venus", "Jupiter", "Mars", "Saturn")
                        if ph.get(n) == h2_from_sun]
        vasi_planets = [n for n in ("Mercury", "Venus", "Jupiter", "Mars", "Saturn")
                        if ph.get(n) == h12_from_sun]
        if vesi_planets and vasi_planets:
            found.append({
                "name": "Ubhayachari Yoga",
                "planets": f"{', '.join(vesi_planets)} (2nd) + {', '.join(vasi_planets)} (12th) from Sun",
                "house": f"Sun H{sun_h}",
                "description": "Planets on both sides of the Sun grant fame, wealth, and noble character.",
                "effect": "Highly Benefic",
            })
        elif vesi_planets:
            found.append({
                "name": "Vesi Yoga",
                "planets": ", ".join(vesi_planets),
                "house": h2_from_sun,
                "description": "Planet in 2nd from Sun grants eloquence, wealth, and good reputation.",
                "effect": "Benefic",
            })
        elif vasi_planets:
            found.append({
                "name": "Vasi Yoga",
                "planets": ", ".join(vasi_planets),
                "house": h12_from_sun,
                "description": "Planet in 12th from Sun grants charitable nature, authority, and fame.",
                "effect": "Benefic",
            })

    # Amala Yoga: benefic in 10th from Moon or Lagna
    benefic_names = {"Jupiter", "Venus", "Mercury"}
    asc_h = next((p.house for p in planets if p.name == "Ascendant"), None)
    if moon_h is not None:
        h10_from_moon = _houses_from_ref(moon_h, 9)
        amala_from_moon = [n for n in benefic_names if ph.get(n) == h10_from_moon]
        if amala_from_moon:
            found.append({
                "name": "Amala Yoga",
                "planets": ", ".join(amala_from_moon),
                "house": h10_from_moon,
                "description": "Benefic in 10th from Moon grants a spotless reputation and virtuous career.",
                "effect": "Benefic",
            })
    if asc_h is not None and (moon_h is None or _houses_from_ref(asc_h, 9) != _houses_from_ref(moon_h, 9)):
        h10_from_asc = _houses_from_ref(asc_h, 9)
        amala_from_asc = [n for n in benefic_names if ph.get(n) == h10_from_asc]
        if amala_from_asc:
            found.append({
                "name": "Amala Yoga (from Lagna)",
                "planets": ", ".join(amala_from_asc),
                "house": h10_from_asc,
                "description": "Benefic in 10th from Lagna grants charitable deeds and lasting fame.",
                "effect": "Benefic",
            })

    # Saraswati Yoga: Jupiter, Venus, Mercury all in kendra/trikona/2nd
    saraswati_houses = KENDRA_HOUSES | TRIKONA_HOUSES | {2}
    if all(ph.get(p) in saraswati_houses for p in ("Jupiter", "Venus", "Mercury") if ph.get(p) is not None):
        if ph.get("Jupiter") and ph.get("Venus") and ph.get("Mercury"):
            found.append({
                "name": "Saraswati Yoga",
                "planets": "Jupiter + Venus + Mercury",
                "house": f"Ju H{ph['Jupiter']}, Ve H{ph['Venus']}, Me H{ph['Mercury']}",
                "description": "Jupiter, Venus, and Mercury in auspicious houses grant mastery in arts, knowledge, and wisdom.",
                "effect": "Highly Benefic",
            })

    if not found:
        found.append({
            "name": "No Major Yoga Detected",
            "planets": "—",
            "house": "—",
            "description": "Standard planetary positions without major yoga formations.",
            "effect": "Neutral",
        })

    return found


def render_yogas(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    yogas = _detect_yogas(data.planets, data.houses)

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("yogas.html")
    return template.render(
        yogas=yogas,
        narratives=data.narratives,
        locale=locale,
        lang=lang,
    )

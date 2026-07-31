"""Ten hand-built charts, specified by longitude rather than by birth data.

The spec's Part 9 asks for a regression corpus containing deliberately awkward charts. Real
birth data cannot be *aimed* at those cases — you would be searching for a date whose Moon
happens to land in Gandanta. Specifying the longitudes directly makes each fixture exactly
the case its name claims, and keeps the whole corpus offline and instantaneous.

Every chart is a genuine ``KundliData``, so anything that accepts a real API response accepts
these unchanged. The API's own label fields (``sign``, ``nakshatra``, ``house``) are filled in
from the longitude by ``_planet()`` so the adapter's cross-check has something consistent to
compare against — a fixture that disagreed with itself would produce warnings that mean
nothing.
"""
from __future__ import annotations

from app.astro.normalise import nakshatra_at
from models import HoroChartSign, KundliData, KundliRequest, PlanetData

_SIGN_NAMES = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)

_SIGN_LORDS = (
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter",
)

_PLANET_IDS = {
    "Ascendant": 0, "Sun": 1, "Moon": 2, "Mars": 3, "Mercury": 4,
    "Jupiter": 5, "Venus": 6, "Saturn": 7, "Rahu": 8, "Ketu": 9,
}

_ORDER = ("Ascendant", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
          "Rahu", "Ketu")


def deg(sign: int, degree: float) -> float:
    """Absolute sidereal longitude from a 1-indexed sign and a degree within it.

    ``deg(3, 0.02)`` is 0°01' Gemini — the reference chart's Venus, and the reason
    ``is_rashi_sandhi`` exists.
    """
    if not 1 <= sign <= 12:
        raise ValueError(f"sign must be 1-12, got {sign}")
    return (sign - 1) * 30.0 + degree


def _planet(name: str, longitude: float, lagna_sign: int, retro: bool, speed: float) -> PlanetData:
    """One PlanetData, with its label fields filled in from the longitude.

    The nakshatra label comes from ``nakshatra_at`` rather than being recomputed here. These
    fixtures stand in for an API response, and a real response is internally consistent — a
    fixture that disagreed with itself would raise adapter warnings that mean nothing about
    the adapter. Tests that need a *wrong* label set it explicitly after construction.
    """
    sign_index = int(longitude // 30)
    nakshatra, pada = nakshatra_at(longitude)
    return PlanetData(
        id=_PLANET_IDS[name],
        name=name,
        fullDegree=longitude,
        normDegree=longitude % 30.0,
        speed=speed,
        sign=_SIGN_NAMES[sign_index],
        signLord=_SIGN_LORDS[sign_index],
        nakshatra=nakshatra.en,
        nakshatraLord=nakshatra.lord.value,
        nakshatra_pad=pada,
        house=((sign_index + 1 - lagna_sign) % 12) + 1,
        isRetro="true" if retro else "false",
    )


def horo_chart(placements: dict[str, int]) -> list[HoroChartSign]:
    """A 12-entry divisional chart from a ``{planet_name: sign_id}`` mapping.

    This is the shape ``/horo_chart/{id}`` returns: sign-level placements with no degrees,
    which is all the varga module needs for vargottama and Vimshopaka Bala.
    """
    by_sign: dict[int, list[str]] = {s: [] for s in range(1, 13)}
    for planet, sign in placements.items():
        by_sign[sign].append(planet)
    return [
        HoroChartSign(
            sign=sign,
            sign_name=_SIGN_NAMES[sign - 1],
            planet=by_sign[sign],
            planet_small=[p[:2] for p in by_sign[sign]],
        )
        for sign in range(1, 13)
    ]


def build(
    *,
    name: str,
    longitudes: dict[str, float],
    retrograde: tuple[str, ...] = (),
    year: int = 1990,
    month: int = 6,
    day: int = 15,
    hour: int = 10,
    minute: int = 30,
    lat: float = 28.6139,
    lon: float = 77.2090,
    tzone: float = 5.5,
    place: str = "New Delhi",
    horo_charts: dict[str, list[HoroChartSign]] | None = None,
) -> KundliData:
    """Assemble a ``KundliData`` from explicit longitudes.

    ``longitudes`` must contain "Ascendant" plus every graha the chart is meant to have.
    Omitting one is how the degradation paths get tested, so it is not validated here.
    """
    lagna_longitude = longitudes.get("Ascendant", 0.0)
    lagna_sign = int(lagna_longitude // 30) + 1

    planets = [
        _planet(
            body,
            longitudes[body],
            lagna_sign,
            body in retrograde,
            -0.05 if body in ("Rahu", "Ketu") else 1.0,
        )
        for body in _ORDER
        if body in longitudes
    ]

    return KundliData(
        request=KundliRequest(
            name=name, day=day, month=month, year=year, hour=hour, min=minute,
            lat=lat, lon=lon, tzone=tzone, place=place,
        ),
        planets=planets,
        horo_charts=horo_charts,
    )


# --- The corpus ---------------------------------------------------------------------------

#: Moon in the last 3°20' of Pisces — the Revati/Ashwini junction. Also carries four planets
#: at their exact exaltation degrees, and Mercury at exactly 15° Virgo, which is the boundary
#: where exaltation hands over to Moolatrikona.
GANDANTA_MOON = build(
    name="Gandanta Moon",
    longitudes={
        "Ascendant": deg(1, 15.0),
        "Sun": deg(5, 10.0),
        "Moon": deg(12, 28.5),
        "Mars": deg(10, 28.0),
        "Mercury": deg(6, 15.0),
        "Jupiter": deg(4, 5.0),
        "Venus": deg(2, 12.0),
        "Saturn": deg(7, 20.0),
        "Rahu": deg(3, 10.0),
        "Ketu": deg(9, 10.0),
    },
    retrograde=("Rahu", "Ketu"),
)

#: The reference chart's structural weakness: Venus at 0°01' Gemini, plus Jupiter at exactly
#: 0°00' Sagittarius. Both are rashi-sandhi; neither may be described as comfortably placed.
RASHI_SANDHI = build(
    name="Rashi Sandhi",
    longitudes={
        "Ascendant": deg(8, 26.45),
        "Sun": deg(4, 28.92),
        "Moon": deg(11, 25.18),
        "Mars": deg(2, 26.33),
        "Mercury": deg(5, 12.76),
        "Jupiter": deg(9, 0.0),
        "Venus": deg(3, 0.02),
        "Saturn": deg(10, 9.82),
        "Rahu": deg(10, 19.15),
        "Ketu": deg(4, 19.15),
    },
    retrograde=("Saturn", "Rahu", "Ketu"),
)

#: Five debilitated planets, with Mars's dispositor (an exalted Moon) in a kendra from the
#: Lagna — classical Neechabhanga condition (a). The yoga engine will need this chart to
#: prove it reports *which* condition fired rather than asserting a bare cancellation.
DEBILITATION_HEAVY = build(
    name="Debilitation Heavy",
    longitudes={
        "Ascendant": deg(11, 8.0),
        "Sun": deg(7, 12.0),
        "Moon": deg(2, 2.0),
        "Mars": deg(4, 10.0),
        "Mercury": deg(8, 20.0),
        "Jupiter": deg(10, 8.0),
        "Venus": deg(6, 15.0),
        "Saturn": deg(1, 12.0),
        "Rahu": deg(5, 5.0),
        "Ketu": deg(11, 5.0),
    },
)

#: All seven grahas hemmed between Rahu at 5° Aries and Ketu at 5° Libra — a complete
#: Kaal Sarp axis with no planet breaking it.
KAAL_SARP = build(
    name="Kaal Sarp",
    longitudes={
        "Ascendant": deg(2, 10.0),
        "Sun": deg(2, 15.0),
        "Moon": deg(3, 20.0),
        "Mars": deg(4, 25.0),
        "Mercury": deg(2, 20.0),
        "Jupiter": deg(5, 10.0),
        "Venus": deg(3, 5.0),
        "Saturn": deg(6, 10.0),
        "Rahu": deg(1, 5.0),
        "Ketu": deg(7, 5.0),
    },
    retrograde=("Rahu", "Ketu"),
)

#: Saturn in Gemini, the 12th from a Cancer Moon — the rising phase of Sade Sati. The dosha
#: module must date this from real transit positions rather than render an em-dash (defect #6).
SADE_SATI_RISING = build(
    name="Sade Sati Rising",
    longitudes={
        "Ascendant": deg(6, 22.0),
        "Sun": deg(1, 8.0),
        "Moon": deg(4, 18.0),
        "Mars": deg(8, 3.0),
        "Mercury": deg(1, 25.0),
        "Jupiter": deg(12, 14.0),
        "Venus": deg(2, 8.0),
        "Saturn": deg(3, 12.0),
        "Rahu": deg(11, 16.0),
        "Ketu": deg(5, 16.0),
    },
)

#: A 1962 birth. Pre-1970 dates break naive epoch arithmetic, and this one also has Mercury
#: 7° from the Sun, so it exercises combustion at the same time.
PRE_1970 = build(
    name="Pre 1970",
    year=1962, month=3, day=14, hour=4, minute=55,
    longitudes={
        "Ascendant": deg(9, 4.0),
        "Sun": deg(10, 20.0),
        "Moon": deg(6, 9.0),
        "Mars": deg(11, 17.0),
        "Mercury": deg(10, 27.0),
        "Jupiter": deg(11, 2.0),
        "Venus": deg(9, 11.0),
        "Saturn": deg(10, 3.0),
        "Rahu": deg(4, 22.0),
        "Ketu": deg(10, 22.0),
    },
    retrograde=("Rahu", "Ketu"),
)

#: Tromsø, 69.6°N. Sunrise-dependent computations (Panchang, Tara Bala, Muhurta) degenerate at
#: polar latitudes; this fixture is here so that degeneration is discovered by a test rather
#: than by an NRI customer.
POLAR_BIRTH = build(
    name="Polar Birth",
    year=1985, month=12, day=21, hour=11, minute=0,
    lat=69.6492, lon=18.9553, tzone=1.0, place="Tromso",
    longitudes={
        "Ascendant": deg(10, 6.0),
        "Sun": deg(9, 5.0),
        "Moon": deg(1, 21.0),
        "Mars": deg(8, 28.0),
        "Mercury": deg(9, 19.0),
        "Jupiter": deg(10, 24.0),
        "Venus": deg(8, 2.0),
        "Saturn": deg(8, 11.0),
        "Rahu": deg(2, 13.0),
        "Ketu": deg(8, 13.0),
    },
)

#: Mercury 3° from the Sun and the Moon 9° from it — two combustions of different orbs, so a
#: single hardcoded orb cannot pass. Venus is retrograde inside its tighter 8° orb.
COMBUSTION_CLUSTER = build(
    name="Combustion Cluster",
    longitudes={
        "Ascendant": deg(3, 17.0),
        "Sun": deg(7, 15.0),
        "Moon": deg(7, 24.0),
        "Mars": deg(1, 9.0),
        "Mercury": deg(7, 18.0),
        "Jupiter": deg(6, 27.0),
        "Venus": deg(7, 21.0),
        "Saturn": deg(12, 6.0),
        "Rahu": deg(9, 28.0),
        "Ketu": deg(3, 28.0),
    },
    retrograde=("Venus", "Rahu", "Ketu"),
)

#: The three degree-split cases in one chart: the Moon at 4° Taurus (past the 3° exaltation
#: arc, so Moolatrikona), Mercury at 17° Virgo (past 15°, so Moolatrikona) and Mercury's own
#: sign Gemini left empty so the fall-through is unambiguous.
EXALTATION_SPLIT = build(
    name="Exaltation Split",
    longitudes={
        "Ascendant": deg(4, 11.0),
        "Sun": deg(1, 10.0),
        "Moon": deg(2, 4.0),
        "Mars": deg(9, 23.0),
        "Mercury": deg(6, 17.0),
        "Jupiter": deg(4, 22.0),
        "Venus": deg(12, 27.0),
        "Saturn": deg(11, 5.0),
        "Rahu": deg(7, 2.0),
        "Ketu": deg(1, 2.0),
    },
)

#: A D1/D9 pair where the Sun holds Leo in both charts — vargottama — and Saturn does not.
#: The ``horo_charts`` payload is the shape ``/horo_chart/{id}`` actually returns.
VARGOTTAMA = build(
    name="Vargottama Sun",
    longitudes={
        "Ascendant": deg(5, 13.0),
        "Sun": deg(5, 21.0),
        "Moon": deg(9, 6.0),
        "Mars": deg(3, 14.0),
        "Mercury": deg(4, 29.0),
        "Jupiter": deg(11, 17.0),
        "Venus": deg(6, 8.0),
        "Saturn": deg(2, 25.0),
        "Rahu": deg(12, 19.0),
        "Ketu": deg(6, 19.0),
    },
    horo_charts={
        "D9": horo_chart({
            "Ascendant": 9, "Sun": 5, "Moon": 1, "Mars": 8, "Mercury": 12,
            "Jupiter": 3, "Venus": 10, "Saturn": 7, "Rahu": 4, "Ketu": 10,
        }),
        "D10": horo_chart({
            "Ascendant": 2, "Sun": 11, "Moon": 6, "Mars": 4, "Mercury": 9,
            "Jupiter": 1, "Venus": 8, "Saturn": 12, "Rahu": 5, "Ketu": 11,
        }),
        "D12": horo_chart({
            "Ascendant": 7, "Sun": 5, "Moon": 2, "Mars": 10, "Mercury": 3,
            "Jupiter": 6, "Venus": 1, "Saturn": 9, "Rahu": 8, "Ketu": 2,
        }),
    },
)

#: Every chart in the corpus, for the tests that must hold on all of them.
CORPUS: dict[str, KundliData] = {
    "gandanta_moon": GANDANTA_MOON,
    "rashi_sandhi": RASHI_SANDHI,
    "debilitation_heavy": DEBILITATION_HEAVY,
    "kaal_sarp": KAAL_SARP,
    "sade_sati_rising": SADE_SATI_RISING,
    "pre_1970": PRE_1970,
    "polar_birth": POLAR_BIRTH,
    "combustion_cluster": COMBUSTION_CLUSTER,
    "exaltation_split": EXALTATION_SPLIT,
    "vargottama": VARGOTTAMA,
}

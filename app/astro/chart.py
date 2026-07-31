"""The adapter: ``KundliData`` (raw AstrologyAPI DTO) in, a typed ``Chart`` out.

Everything else in ``app.astro`` is pure math over dictionaries. This module is the one
place that knows what an API response looks like, which is deliberate — when AstrologyAPI
changes a field name, exactly one file needs editing.

Two rules it enforces, both of them LAW 1 (single source of truth):

**Longitude wins over labels.** ``PlanetData.fullDegree`` is the sidereal longitude and is
language-independent; ``sign``, ``nakshatra`` and ``house`` are strings whose language
follows the request. So sign, degree, nakshatra, pada and house are all *derived* here from
the longitude, and the API's own labels are only used to cross-check. A disagreement is
recorded in ``Chart.warnings`` and logged — it never changes the answer.

**Compute once.** Dignity, avastha, combustion, gandanta and rashi-sandhi are resolved here
and frozen onto ``PlanetPosition``. No section may recompute them; the ``dignity_consistency``
gate check compares the rendered HTML against these values.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.astro.ashtakavarga import AshtakavargaData, compute_ashtakavarga
from app.astro.dignity import (
    Combustion,
    baladi_avastha,
    combustion,
    deeptadi_avastha,
    dignity_of,
    exaltation_orb,
    is_gandanta,
    is_rashi_sandhi,
)
from app.astro.enums import SAPTA_GRAHA, BaladiAvastha, Dignity, Graha, Rashi
from app.astro.normalise import (
    Nakshatra,
    is_ascendant,
    nakshatra_at,
    normalise_longitude,
    rashi_at,
    try_resolve_graha,
    try_resolve_nakshatra,
    try_resolve_rashi,
)

logger = logging.getLogger(__name__)

# Bodies the API returns that are not one of the nine grahas. They are recognised so they
# can be skipped quietly rather than logged as unresolvable names on every single chart.
_NON_GRAHA_BODIES = frozenset({"uranus", "neptune", "pluto", "chiron"})


class ChartDataError(ValueError):
    """The response is missing something no amount of graceful degradation can cover.

    Only three bodies qualify: the Ascendant (every house number counts from it), the Moon
    (the entire dasha timeline hangs off its longitude) and the Sun (combustion is measured
    from it). Anything else missing produces a warning and a smaller chart.
    """


@dataclass(frozen=True, slots=True)
class NakshatraReading:
    """One nakshatra placement, fully populated or not constructed at all.

    The ``nakshatra_complete`` gate check asserts all three readings in ``NakshatraTrio``
    exist. Because ``nakshatra_at()`` derives from longitude, "details unavailable" (defect
    #7) is unreachable: there is no code path that produces a name without its data.
    """

    nakshatra: Nakshatra
    pada: int
    longitude: float

    @property
    def lord(self) -> Graha:
        return self.nakshatra.lord

    def label(self, lang: str) -> str:
        return self.nakshatra.label(lang)


@dataclass(frozen=True, slots=True)
class NakshatraTrio:
    """Janma (Moon), Surya (Sun) and Lagna nakshatras — §15 renders all three."""

    janma: NakshatraReading
    surya: NakshatraReading
    lagna: NakshatraReading

    def as_dict(self) -> dict[str, NakshatraReading]:
        return {"janma": self.janma, "surya": self.surya, "lagna": self.lagna}


@dataclass(frozen=True, slots=True)
class PlanetPosition:
    """Everything §10 prints about one graha, computed once and frozen."""

    graha: Graha
    longitude: float
    sign: Rashi
    degree_in_sign: float
    nakshatra: Nakshatra
    pada: int
    house: int                       # whole-sign, counted from the Lagna sign
    is_retrograde: bool
    speed: float
    dignity: Dignity
    baladi: BaladiAvastha
    deeptadi: str
    combustion: Combustion
    is_gandanta: bool
    is_rashi_sandhi: bool
    exaltation_orb: float | None     # degrees from deep exaltation, None if not in that sign

    @property
    def sign_lord(self) -> Graha:
        return self.sign.lord

    @property
    def nakshatra_lord(self) -> Graha:
        return self.nakshatra.lord

    @property
    def is_combust(self) -> bool:
        return self.combustion.is_combust

    @property
    def needs_hedging(self) -> bool:
        """Structural weakness that must temper any promise made through this planet.

        Part 12 of the spec: a planet at 0.02° of a sign is barely functional, a gandanta
        planet sits on a seam, a combust planet is overwhelmed. The narrative layer reads
        this rather than each prompt re-deriving the same three conditions.
        """
        return self.is_rashi_sandhi or self.is_gandanta or self.is_combust


@dataclass(frozen=True, slots=True)
class LagnaPosition:
    """The Ascendant. Not a graha — no dignity, no avastha, no combustion.

    Kept as its own type rather than a ``PlanetPosition`` with null fields, so a template
    cannot print "the Ascendant is in a friend's sign", which is meaningless.
    """

    longitude: float
    sign: Rashi
    degree_in_sign: float
    nakshatra: Nakshatra
    pada: int
    is_gandanta: bool
    is_rashi_sandhi: bool

    @property
    def sign_lord(self) -> Graha:
        return self.sign.lord

    @property
    def nakshatra_lord(self) -> Graha:
        return self.nakshatra.lord


@dataclass(frozen=True, slots=True)
class HouseInfo:
    """One whole-sign bhava. ``lord_house`` is where that lord actually sits — the single
    fact most yoga rules ask for, so it is precomputed rather than looked up per rule."""

    number: int
    sign: Rashi
    lord: Graha
    occupants: tuple[Graha, ...]
    lord_house: int | None           # None when the lord itself is missing from the chart


@dataclass(frozen=True, slots=True)
class Chart:
    """The assembled natal chart. Input to every other module in ``app.astro``."""

    planets: dict[Graha, PlanetPosition]
    lagna: LagnaPosition
    houses: tuple[HouseInfo, ...]
    nakshatras: NakshatraTrio
    ashtakavarga: AshtakavargaData | None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def sun(self) -> PlanetPosition:
        return self.planets[Graha.SUN]

    @property
    def moon(self) -> PlanetPosition:
        return self.planets[Graha.MOON]

    def sign_of(self, graha: Graha) -> Rashi | None:
        position = self.planets.get(graha)
        return position.sign if position else None

    def house_of(self, graha: Graha) -> int | None:
        position = self.planets.get(graha)
        return position.house if position else None

    def occupants_of(self, house: int) -> tuple[Graha, ...]:
        return self.houses[house - 1].occupants

    def longitudes(self) -> dict[Graha, float]:
        return {graha: p.longitude for graha, p in self.planets.items()}

    def signs(self) -> dict[Graha, Rashi]:
        return {graha: p.sign for graha, p in self.planets.items()}


# --- Extraction ---------------------------------------------------------------------------


def _is_retrograde(raw: object) -> bool:
    """``PlanetData.isRetro`` is a *string* — "true"/"false" — not a bool. A truthiness test
    on it would make every planet retrograde, since "false" is a non-empty string."""
    return str(raw).strip().lower() in ("true", "1", "yes", "y")


def _house_from_lagna(sign: Rashi, lagna_sign: Rashi) -> int:
    """Whole-sign house number, 1-12. The house system is declared on the birth-details page."""
    return ((sign.value - lagna_sign.value) % 12) + 1


def _collect_longitudes(
    data,
    warnings: list[str],
) -> tuple[dict[Graha, tuple[float, float, bool, str]], float | None]:
    """Pull (longitude, speed, retrograde, api_nakshatra_label) per graha, plus the Lagna.

    ``data.planets`` carries the Ascendant as a pseudo-planet named "Ascendant" with id 0.
    ``planets_extended`` covers the same nine plus the outer bodies, so it is merged in only
    for grahas the primary list is missing — never to override one it already has.
    """
    raw_bodies: dict[Graha, tuple[float, float, bool, str]] = {}
    lagna_longitude: float | None = None

    for source in (data.planets or [], data.planets_extended or []):
        for entry in source:
            name = (entry.name or "").strip()
            if not name:
                continue
            longitude = normalise_longitude(entry.fullDegree)

            if is_ascendant(name):
                if lagna_longitude is None:
                    lagna_longitude = longitude
                continue

            graha = try_resolve_graha(name)
            if graha is None:
                if name.lower() not in _NON_GRAHA_BODIES:
                    warnings.append(f"Unrecognised body in planets list: {name!r}")
                continue
            if graha in raw_bodies:
                continue
            raw_bodies[graha] = (
                longitude,
                float(entry.speed or 0.0),
                _is_retrograde(entry.isRetro),
                (entry.nakshatra or "").strip(),
            )

    return raw_bodies, lagna_longitude


def _derive_ketu(
    raw_bodies: dict[Graha, tuple[float, float, bool, str]],
    warnings: list[str],
) -> None:
    """Ketu is always exactly opposite Rahu. Deriving it beats dropping a graha from a report
    that has nine planet sections — but it is recorded as a warning, because a response that
    omits Ketu may be truncated in other ways too."""
    if Graha.KETU in raw_bodies or Graha.RAHU not in raw_bodies:
        return
    rahu_longitude, speed, retro, _ = raw_bodies[Graha.RAHU]
    raw_bodies[Graha.KETU] = (normalise_longitude(rahu_longitude + 180.0), speed, retro, "")
    warnings.append("Ketu absent from the API response; derived as Rahu + 180°")


def _check_label(
    graha: Graha,
    api_label: str,
    derived: Nakshatra,
    warnings: list[str],
) -> None:
    """Cross-check the API's nakshatra string against the longitude-derived one.

    A mismatch means either the ayanamsa differs from what we assume or a planet sits within
    minutes of a nakshatra boundary. Both are worth knowing; neither changes the answer.
    """
    if not api_label:
        return
    resolved = try_resolve_nakshatra(api_label)
    if resolved is None:
        warnings.append(f"{graha.value}: API nakshatra {api_label!r} did not resolve")
    elif resolved.index != derived.index:
        warnings.append(
            f"{graha.value}: API says nakshatra {resolved.en}, longitude says {derived.en}"
        )


def _build_houses(
    lagna_sign: Rashi,
    positions: dict[Graha, PlanetPosition],
) -> tuple[HouseInfo, ...]:
    occupants: dict[int, list[Graha]] = {n: [] for n in range(1, 13)}
    for graha, position in positions.items():
        occupants[position.house].append(graha)

    houses: list[HouseInfo] = []
    for number in range(1, 13):
        sign = Rashi(((lagna_sign.value - 1 + number - 1) % 12) + 1)
        lord = sign.lord
        lord_position = positions.get(lord)
        houses.append(
            HouseInfo(
                number=number,
                sign=sign,
                lord=lord,
                # Sorted so the same chart always yields the same order — the golden-file
                # snapshot tests depend on dict iteration never leaking into output.
                occupants=tuple(sorted(occupants[number], key=lambda g: list(Graha).index(g))),
                lord_house=lord_position.house if lord_position else None,
            )
        )
    return tuple(houses)


def build_chart(data) -> Chart:
    """Assemble a ``Chart`` from a ``KundliData``.

    Pure: no network, no clock, no filesystem. ``data`` is typed loosely to keep this module
    importable without pulling in ``models`` (and through it pydantic) at import time — the
    only attributes touched are ``planets``, ``planets_extended`` and ``houses``.

    Raises ``ChartDataError`` when the Ascendant, Sun or Moon is missing. That is fail-closed
    by design (LAW 3): a chart without a Lagna has no house numbers, and every one of the 29
    sections would be quietly wrong rather than visibly absent.
    """
    warnings: list[str] = []
    raw_bodies, lagna_longitude = _collect_longitudes(data, warnings)
    _derive_ketu(raw_bodies, warnings)

    if lagna_longitude is None:
        lagna_longitude = _lagna_from_houses(data, warnings)
    if lagna_longitude is None:
        raise ChartDataError("No Ascendant in the response — house numbers cannot be derived")
    for required in (Graha.SUN, Graha.MOON):
        if required not in raw_bodies:
            raise ChartDataError(f"No {required.value} in the response")

    lagna_sign, lagna_degree = rashi_at(lagna_longitude)
    lagna_nakshatra, lagna_pada = nakshatra_at(lagna_longitude)
    lagna = LagnaPosition(
        longitude=lagna_longitude,
        sign=lagna_sign,
        degree_in_sign=lagna_degree,
        nakshatra=lagna_nakshatra,
        pada=lagna_pada,
        is_gandanta=is_gandanta(lagna_longitude),
        is_rashi_sandhi=is_rashi_sandhi(lagna_longitude),
    )

    longitudes = {graha: values[0] for graha, values in raw_bodies.items()}
    signs = {graha: rashi_at(lon)[0] for graha, lon in longitudes.items()}
    sun_longitude = longitudes[Graha.SUN]

    positions: dict[Graha, PlanetPosition] = {}
    for graha in Graha:
        if graha not in raw_bodies:
            warnings.append(f"{graha.value} absent from the API response")
            continue
        longitude, speed, retrograde, api_nakshatra = raw_bodies[graha]
        sign, degree = rashi_at(longitude)
        nakshatra, pada = nakshatra_at(longitude)
        _check_label(graha, api_nakshatra, nakshatra, warnings)

        dignity = dignity_of(graha, longitude, signs)
        burn = combustion(graha, longitude, sun_longitude, retrograde)
        positions[graha] = PlanetPosition(
            graha=graha,
            longitude=longitude,
            sign=sign,
            degree_in_sign=degree,
            nakshatra=nakshatra,
            pada=pada,
            house=_house_from_lagna(sign, lagna_sign),
            is_retrograde=retrograde,
            speed=speed,
            dignity=dignity,
            baladi=baladi_avastha(longitude),
            deeptadi=deeptadi_avastha(graha, dignity, burn.is_combust),
            combustion=burn,
            is_gandanta=is_gandanta(longitude),
            is_rashi_sandhi=is_rashi_sandhi(longitude),
            exaltation_orb=exaltation_orb(graha, longitude),
        )

    _cross_check_houses(data, positions, warnings)

    nakshatras = NakshatraTrio(
        janma=NakshatraReading(
            positions[Graha.MOON].nakshatra, positions[Graha.MOON].pada,
            positions[Graha.MOON].longitude,
        ),
        surya=NakshatraReading(
            positions[Graha.SUN].nakshatra, positions[Graha.SUN].pada,
            positions[Graha.SUN].longitude,
        ),
        lagna=NakshatraReading(lagna.nakshatra, lagna.pada, lagna.longitude),
    )

    ashtakavarga: AshtakavargaData | None = None
    missing_for_av = [g for g in SAPTA_GRAHA if g not in positions]
    if missing_for_av:
        warnings.append(
            "Ashtakavarga skipped; missing " + ", ".join(g.value for g in missing_for_av)
        )
    else:
        ashtakavarga = compute_ashtakavarga(
            {graha: positions[graha].sign for graha in SAPTA_GRAHA}, lagna_sign
        )

    for message in warnings:
        logger.warning("chart: %s", message)

    return Chart(
        planets=positions,
        lagna=lagna,
        houses=_build_houses(lagna_sign, positions),
        nakshatras=nakshatras,
        ashtakavarga=ashtakavarga,
        warnings=tuple(warnings),
    )


def _lagna_from_houses(data, warnings: list[str]) -> float | None:
    """Last-resort Lagna recovery from the ``/houses`` response.

    ``HouseData`` for house 1 carries the ascendant's sign and its degree within that sign,
    which reconstructs the longitude exactly. Used only when the planets list omits the
    Ascendant entirely.
    """
    houses = getattr(data, "houses", None) or []
    for house in houses:
        if getattr(house, "house_id", 0) != 1:
            continue
        sign = try_resolve_rashi(getattr(house, "sign_id", 0) or getattr(house, "sign", ""))
        if sign is None:
            continue
        degree = float(getattr(house, "degree", 0.0) or 0.0) % 30.0
        warnings.append("Ascendant taken from the houses response, not the planets list")
        return (sign.value - 1) * 30.0 + degree
    return None


def _cross_check_houses(
    data,
    positions: dict[Graha, PlanetPosition],
    warnings: list[str],
) -> None:
    """Compare our whole-sign house numbers against the ones the API returned.

    The API uses whole-sign too, so these should agree exactly. When they don't, the usual
    cause is a different ayanamsa on a planet sitting within minutes of a sign boundary —
    which is precisely the case ``is_rashi_sandhi`` already flags. Ours wins either way.
    """
    for entry in data.planets or []:
        graha = try_resolve_graha((entry.name or "").strip()) if entry.name else None
        if graha is None or graha not in positions:
            continue
        api_house = int(entry.house or 0)
        if api_house and api_house != positions[graha].house:
            warnings.append(
                f"{graha.value}: API house {api_house}, whole-sign from Lagna gives "
                f"{positions[graha].house}"
            )

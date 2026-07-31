"""Vimshottari Dasha — the one place in the codebase that answers "when".

This module exists to make defect #1 impossible. The reference report stated the same Sun
Antardasha ending in December 2027, December 2026 and April 2027 in three different sections,
because three different code paths each derived it. Here there is exactly one derivation and
exactly one accessor, ``DashaTimeline.active_periods()``. No section may compute a dasha date
any other way, and ``ActivePeriods.label()`` is the only sanctioned rendering of the current
period — the ``dasha_single_truth`` gate check asserts that identical string appears in every
section that mentions it.

**Computed here, not fetched.** ``api_client`` returns sub-periods only for the *current*
MD/AD/PD path, so a five-level timeline is not obtainable from the API without thousands of
calls. Below the Moon's nakshatra, Vimshottari is pure proportional arithmetic, so the whole
timeline is derived locally and the API's own dasha response is used as a cross-check
(``cross_check_against_api``) that logs divergence rather than overriding anything.

**Eager to level 3, exact below.** Levels 1-3 (819 periods) are materialised because every
table in the report renders them. Levels 4 and 5 would be ~66,000 more objects per request
across four workers, so they are subdivided on demand from the period that contains them.
The arithmetic is identical either way; only the memory differs.
"""
from __future__ import annotations

import logging
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone

from app.astro.enums import Graha
from app.astro.normalise import nakshatra_at, nakshatra_elapsed_fraction, try_resolve_graha

logger = logging.getLogger(__name__)

#: The Vimshottari sequence and each lord's period in years. The ORDER is load-bearing — it
#: is the same cycle the 27 nakshatra lords run in (``normalise.NAKSHATRAS``), which is what
#: makes the balance at birth computable from the Moon's longitude alone. Do not sort it.
VIMSHOTTARI_YEARS: dict[Graha, int] = {
    Graha.KETU: 7,
    Graha.VENUS: 20,
    Graha.SUN: 6,
    Graha.MOON: 10,
    Graha.MARS: 7,
    Graha.RAHU: 18,
    Graha.JUPITER: 16,
    Graha.SATURN: 19,
    Graha.MERCURY: 17,
}

VIMSHOTTARI_ORDER: tuple[Graha, ...] = tuple(VIMSHOTTARI_YEARS)
TOTAL_YEARS = 120
assert sum(VIMSHOTTARI_YEARS.values()) == TOTAL_YEARS, "Vimshottari must sum to 120 years"

#: The savana year. Every other Vedic astrology package makes the same choice, but the value
#: is declared on the birth-details page because it is *why* our dates differ by a day or two
#: from software that uses 365.2425. Internal consistency is the property that matters.
YEAR_DAYS = 365.25

#: Level names, 1-indexed. Level 0 is unused so the list can be indexed by level directly.
LEVEL_NAMES: tuple[str, ...] = (
    "", "Mahadasha", "Antardasha", "Pratyantardasha", "Sookshma", "Prana",
)

LEVEL_NAMES_HI: tuple[str, ...] = (
    "", "महादशा", "अंतर्दशा", "प्रत्यंतर्दशा", "सूक्ष्म दशा", "प्राण दशा",
)

#: Levels materialised eagerly. Everything below is exact but computed on demand.
EAGER_LEVELS = 3
MAX_LEVEL = 5


class DashaError(ValueError):
    """Raised when a timeline cannot be built or queried honestly."""


def _sequence_from(lord: Graha) -> tuple[Graha, ...]:
    """The nine lords starting at ``lord`` — the order sub-periods run in."""
    start = VIMSHOTTARI_ORDER.index(lord)
    return VIMSHOTTARI_ORDER[start:] + VIMSHOTTARI_ORDER[:start]


@dataclass(frozen=True, slots=True)
class DashaPeriod:
    """One period at one level. Intervals are half-open: ``start <= t < end``.

    Half-open is what makes an instant that falls exactly on a boundary belong to exactly one
    period. With closed intervals, midnight on a transition date belongs to two — and which
    one you got would depend on iteration order, which is how a report ends up disagreeing
    with itself.
    """

    level: int
    lord: Graha
    start: datetime
    end: datetime
    parent_path: tuple[Graha, ...] = ()

    @property
    def path(self) -> tuple[Graha, ...]:
        """Lords from Mahadasha down to this one, e.g. ``(Venus, Sun, Jupiter)``."""
        return (*self.parent_path, self.lord)

    @property
    def duration_days(self) -> float:
        return (self.end - self.start).total_seconds() / 86400.0

    def contains(self, at: datetime) -> bool:
        return self.start <= at < self.end

    def level_name(self, lang: str = "en") -> str:
        return (LEVEL_NAMES_HI if lang == "hi" else LEVEL_NAMES)[self.level]

    def label(self, lang: str = "en") -> str:
        """``Venus–Sun–Jupiter`` — the lord chain, in the report language."""
        return "–".join(g.hi if lang == "hi" else g.value for g in self.path)


@dataclass(frozen=True, slots=True)
class ActivePeriods:
    """All five running periods at one instant.

    ``label()`` is the canonical rendering. Every section that names the current dasha must
    call it rather than formatting the lords itself — that is the whole mechanism behind the
    ``dasha_single_truth`` check.
    """

    at: datetime
    maha: DashaPeriod
    antar: DashaPeriod
    pratyantar: DashaPeriod
    sookshma: DashaPeriod
    prana: DashaPeriod

    @property
    def levels(self) -> tuple[DashaPeriod, ...]:
        return (self.maha, self.antar, self.pratyantar, self.sookshma, self.prana)

    @property
    def lords(self) -> tuple[Graha, ...]:
        return tuple(period.lord for period in self.levels)

    def at_level(self, level: int) -> DashaPeriod:
        if not 1 <= level <= MAX_LEVEL:
            raise DashaError(f"Dasha level must be 1-{MAX_LEVEL}, got {level}")
        return self.levels[level - 1]

    def label(self, lang: str = "en", depth: int = 3) -> str:
        """``Venus–Sun–Jupiter`` to the requested depth. The default of 3 (MD/AD/PD) is what
        the running-period panel shows; §20 uses 5."""
        if not 1 <= depth <= MAX_LEVEL:
            raise DashaError(f"depth must be 1-{MAX_LEVEL}, got {depth}")
        return self.at_level(depth).label(lang)


def _subdivide(parent: DashaPeriod) -> tuple[DashaPeriod, ...]:
    """The nine sub-periods of a period, in Vimshottari order starting from its own lord.

    The last child's end is pinned to the parent's end rather than accumulated. Nine
    successive float multiplications drift by microseconds, and a microsecond gap between the
    end of one period and the start of the next is exactly what the ``dasha_continuity``
    check exists to catch. Pinning makes the invariant exact instead of approximate.
    """
    if parent.level >= MAX_LEVEL:
        return ()

    total = parent.end - parent.start
    children: list[DashaPeriod] = []
    cursor = parent.start
    sequence = _sequence_from(parent.lord)

    for index, lord in enumerate(sequence):
        is_last = index == len(sequence) - 1
        end = parent.end if is_last else cursor + total * (VIMSHOTTARI_YEARS[lord] / TOTAL_YEARS)
        children.append(
            DashaPeriod(
                level=parent.level + 1,
                lord=lord,
                start=cursor,
                end=end,
                parent_path=parent.path,
            )
        )
        cursor = end
    return tuple(children)


def _find(periods: tuple[DashaPeriod, ...], at: datetime) -> DashaPeriod | None:
    """Binary search over a contiguous, ascending run of periods."""
    starts = [period.start for period in periods]
    index = bisect_right(starts, at) - 1
    if index < 0:
        return None
    candidate = periods[index]
    return candidate if candidate.contains(at) else None


@dataclass(frozen=True, slots=True)
class DashaTimeline:
    """The Vimshottari timeline for one native."""

    birth: datetime
    moon_longitude: float
    first_lord: Graha
    balance_years: float
    periods: tuple[DashaPeriod, ...]          # levels 1-3, ascending within each level
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def at_level(self, level: int) -> tuple[DashaPeriod, ...]:
        if not 1 <= level <= EAGER_LEVELS:
            raise DashaError(
                f"Only levels 1-{EAGER_LEVELS} are materialised; use active_periods() or "
                f"children() for level {level}"
            )
        return tuple(p for p in self.periods if p.level == level)

    def children(self, parent: DashaPeriod) -> tuple[DashaPeriod, ...]:
        """Sub-periods of any period, materialised or not."""
        return _subdivide(parent)

    def active_periods(self, at: datetime) -> ActivePeriods:
        """The five running periods at ``at`` — **the only dasha accessor in the codebase.**

        ``at`` must be timezone-aware. A naive datetime here would silently compare against
        UTC-aware boundaries and raise, or worse, be off by the birth offset; requiring
        awareness makes the mistake loud.
        """
        if at.tzinfo is None:
            raise DashaError("active_periods() needs a timezone-aware datetime")
        at = at.astimezone(UTC)

        maha = _find(self.at_level(1), at)
        if maha is None:
            raise DashaError(
                f"{at.isoformat()} falls outside the computed timeline "
                f"({self.periods[0].start.isoformat()} to {self.at_level(1)[-1].end.isoformat()})"
            )

        current = maha
        chain = [maha]
        while current.level < MAX_LEVEL:
            children = _subdivide(current)
            found = _find(children, at)
            if found is None:  # pragma: no cover - children exactly tile the parent
                raise DashaError(f"No level-{current.level + 1} period contains {at.isoformat()}")
            chain.append(found)
            current = found

        return ActivePeriods(at, *chain)

    def next_12_transitions(self, at: datetime) -> tuple[DashaPeriod, ...]:
        """Periods beginning within twelve months of ``at``, at levels 2 and 3.

        §23 cross-references these so the transit narrative can say the Jupiter ingress lands
        three weeks into a particular sub-period — which requires the two sections to agree
        on when that sub-period starts, hence reading them from here.
        """
        if at.tzinfo is None:
            raise DashaError("next_12_transitions() needs a timezone-aware datetime")
        at = at.astimezone(UTC)
        horizon = at + timedelta(days=YEAR_DAYS)
        return tuple(
            period
            for period in self.periods
            if period.level in (2, 3) and at <= period.start < horizon
        )

    def mahadashas(self) -> tuple[DashaPeriod, ...]:
        return self.at_level(1)

    def antardashas(self) -> tuple[DashaPeriod, ...]:
        """Every Antardasha in the timeline, ascending.

        There is deliberately no ``by lord`` filter. The timeline spans two 120-year cycles,
        so ``parent_path`` is *not* unique — a Jupiter Mahadasha appears twice, 120 years
        apart, and filtering by lord would silently merge them. To scope to one Mahadasha,
        pass that period to ``children()``, which is unambiguous.
        """
        return self.at_level(2)


def birth_datetime(request) -> datetime:
    """Assemble the tz-aware birth instant from a ``KundliRequest``.

    ``tzone`` is a float offset in hours (5.5 for IST). It is used directly rather than a
    named zone because that is what the API takes and what the customer entered — resolving
    a zone name here would risk applying a DST rule the chart was not cast with.
    """
    try:
        offset = timezone(timedelta(hours=float(request.tzone)))
        local = datetime(
            int(request.year), int(request.month), int(request.day),
            int(request.hour), int(request.min), tzinfo=offset,
        )
    except (TypeError, ValueError) as exc:
        raise DashaError(f"Unusable birth date/time in the request: {exc}") from exc
    return local.astimezone(UTC)


def build_timeline(chart, birth: datetime) -> DashaTimeline:
    """Build the Vimshottari timeline from the Moon's longitude.

    The first Mahadasha's *start* is placed before birth, at the point the full period would
    have begun — so its sub-periods are proportioned over the whole span and the ones already
    elapsed simply fall before birth. Proportioning them over the remaining balance instead
    is a common bug that compresses every early Antardasha.
    """
    if birth.tzinfo is None:
        raise DashaError("build_timeline() needs a timezone-aware birth datetime")
    birth = birth.astimezone(UTC)

    moon_longitude = chart.moon.longitude
    nakshatra, _ = nakshatra_at(moon_longitude)
    first_lord = nakshatra.lord
    elapsed = nakshatra_elapsed_fraction(moon_longitude)
    balance_years = (1.0 - elapsed) * VIMSHOTTARI_YEARS[first_lord]

    warnings: list[str] = []
    if balance_years < 0.05:
        warnings.append(
            f"The Moon is within days of leaving {nakshatra.en}, so the {first_lord.value} "
            f"Mahadasha balance at birth is only {balance_years * YEAR_DAYS:.1f} days"
        )

    first_start = birth - timedelta(days=elapsed * VIMSHOTTARI_YEARS[first_lord] * YEAR_DAYS)

    # Two full cycles cover 240 years from the first Mahadasha's start, which comfortably
    # brackets the 120 years after birth even when the first period is nearly exhausted.
    mahadashas: list[DashaPeriod] = []
    cursor = first_start
    for lord in _sequence_from(first_lord) * 2:
        end = cursor + timedelta(days=VIMSHOTTARI_YEARS[lord] * YEAR_DAYS)
        mahadashas.append(DashaPeriod(level=1, lord=lord, start=cursor, end=end))
        cursor = end

    periods: list[DashaPeriod] = list(mahadashas)
    for maha in mahadashas:
        antardashas = _subdivide(maha)
        periods.extend(antardashas)
        for antar in antardashas:
            periods.extend(_subdivide(antar))

    for message in warnings:
        logger.warning("dasha: %s", message)

    return DashaTimeline(
        birth=birth,
        moon_longitude=moon_longitude,
        first_lord=first_lord,
        balance_years=balance_years,
        periods=tuple(periods),
        warnings=tuple(warnings),
    )


def build_from_data(chart, data) -> DashaTimeline:
    """Convenience: timeline for a ``KundliData``, using its request's birth details."""
    return build_timeline(chart, birth_datetime(data.request))


# --- Cross-check against the API's own dasha response ---------------------------------------

_API_DATE_FORMATS = ("%d-%m-%Y %H:%M", "%d-%m-%Y", "%d-%m-%Y %H:%M:%S")

#: How far our computed boundary may sit from the API's before it is worth reporting. The two
#: use different ayanamsa and rounding, so sub-day differences are expected and uninteresting.
DIVERGENCE_TOLERANCE_DAYS = 2.0


def parse_api_datetime(text: str, offset_hours: float) -> datetime | None:
    """Parse an AstrologyAPI dasha date. They arrive as ``15-8-1990 14:30`` or ``16-8-2012``,
    in the native's local time, so the birth offset is applied to make them comparable."""
    if not text:
        return None
    tz = timezone(timedelta(hours=float(offset_hours)))
    for fmt in _API_DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt).replace(tzinfo=tz).astimezone(UTC)
        except ValueError:
            continue
    return None


def cross_check_against_api(timeline: DashaTimeline, data) -> tuple[str, ...]:
    """Compare our Mahadasha boundaries with the API's, and report divergence.

    Deliberately returns findings instead of correcting anything. The locally computed
    timeline is the single source of truth precisely because it is complete and internally
    consistent; the API's is a second opinion worth logging when it disagrees, not a
    correction to apply.
    """
    findings: list[str] = []
    offset = float(getattr(data.request, "tzone", 0.0) or 0.0)
    api_mahadashas = getattr(data, "major_vdasha", None) or []
    if not api_mahadashas:
        return ()

    api_first = try_resolve_graha(getattr(api_mahadashas[0], "planet", "") or "")
    if api_first is None:
        return ()

    # The sequences are compared by position, not by lord. Both run the same nine lords in
    # the same cycle, so once the starting lord agrees the nth entries describe the same
    # period; if it does *not* agree the two timelines are offset by whole Mahadashas and
    # pairing Ketu with Ketu would report a 46-year "divergence" that means nothing.
    if api_first is not timeline.first_lord:
        findings.append(
            f"The API's first Mahadasha lord is {api_first.value}, but the Moon's longitude "
            f"({timeline.moon_longitude:.4f}°) puts it in a {timeline.first_lord.value} "
            f"nakshatra. Dates were not compared — the sequences are offset."
        )
    else:
        ours = timeline.at_level(1)
        # The API lists the first Mahadasha as starting *at birth* with only the balance
        # remaining, whereas ours starts at the point the full period would have begun. Their
        # starts therefore always differ by the elapsed portion, by construction. What must
        # agree is where the first period *ends* — that single date is the balance at birth,
        # and it is the most informative comparison in this whole function.
        api_first_end = parse_api_datetime(getattr(api_mahadashas[0], "end", "") or "", offset)
        if api_first_end is not None:
            drift = abs((api_first_end - ours[0].end).total_seconds()) / 86400.0
            if drift > DIVERGENCE_TOLERANCE_DAYS:
                findings.append(
                    f"Balance of the {ours[0].lord.value} Mahadasha at birth ends "
                    f"{ours[0].end.date()} locally but {api_first_end.date()} per the API "
                    f"({drift:.1f} days apart)"
                )

        for index, entry in enumerate(api_mahadashas[: len(ours)]):
            if index == 0:
                continue
            api_start = parse_api_datetime(getattr(entry, "start", "") or "", offset)
            if api_start is None:
                continue
            drift = abs((api_start - ours[index].start).total_seconds()) / 86400.0
            if drift > DIVERGENCE_TOLERANCE_DAYS:
                findings.append(
                    f"{ours[index].lord.value} Mahadasha starts {ours[index].start.date()} "
                    f"locally but {api_start.date()} per the API ({drift:.1f} days apart)"
                )

    for message in findings:
        logger.warning("dasha cross-check: %s", message)
    return tuple(findings)

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING


from sections import LOCALES, translate_keys, make_env

if TYPE_CHECKING:
    from models import KundliData

SADHESATI_KEYS_HI: dict[str, str] = {
    "is_undergoing_sadhesati": "साढ़ेसाती चल रही है",
    "sadhesati_status": "साढ़ेसाती स्थिति",
    "is_undergoing_small_panoti": "छोटी पनौती चल रही है",
    "small_panoti_status": "छोटी पनौती स्थिति",
    "consideration_status": "विचार स्थिति",
    "is_undergoing": "चल रहा है",
    "remedies": "उपाय",
}

# The status table mixes one natal value with one transit value under labels that look
# identical ("Moon Sign" / "Saturn Sign"), directly below cards that show *natal*
# Saturn — so the page appeared to place Saturn in two signs at once. Disambiguate both,
# in both languages, via the same translate_keys mechanism SADHESATI_KEYS_HI uses.
STATUS_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "moon_sign": "Natal Moon Sign",
        "saturn_sign": "Saturn Now (Transit)",
    },
    "hi": {
        "moon_sign": "जन्म चंद्र राशि",
        "saturn_sign": "वर्तमान शनि राशि (गोचर)",
    },
}

# The /sadhesati_life_details rows carry the phase as an enum constant
# (RISING_START, PEAK_START, …). Printed raw it leaks into the PDF, so map it.
# Phase names follow the vocabulary already used in locale ss_phases_desc:
# Rising / Peak / Setting -> आरंभ / शिखर / अंत.
PHASE_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "RISING_START": "Rising Phase Begins",
        "RISING_END": "Rising Phase Ends",
        "PEAK_START": "Peak Phase Begins",
        "PEAK_END": "Peak Phase Ends",
        "SETTING_START": "Setting Phase Begins",
        "SETTING_END": "Setting Phase Ends",
    },
    "hi": {
        "RISING_START": "आरंभ चरण प्रारंभ",
        "RISING_END": "आरंभ चरण समाप्त",
        "PEAK_START": "शिखर चरण प्रारंभ",
        "PEAK_END": "शिखर चरण समाप्त",
        "SETTING_START": "अंत चरण प्रारंभ",
        "SETTING_END": "अंत चरण समाप्त",
    },
}


def _entry_date(entry: dict) -> date | None:
    """Parse a life-details row's D-M-YYYY date. Returns None on anything unexpected."""
    raw = entry.get("date") or entry.get("start") or entry.get("start_date")
    if not isinstance(raw, str):
        return None
    parts = raw.strip().split("-")
    if len(parts) != 3:
        return None
    try:
        day, month, year = (int(p) for p in parts)
        return date(year, month, day)
    except (ValueError, TypeError):
        return None


def _entry_key(entry) -> tuple[str, str] | None:
    if not isinstance(entry, dict):
        return None
    return (
        str(entry.get("phase") or entry.get("type") or ""),
        str(entry.get("saturn_sign") or entry.get("sign") or ""),
    )


def dedupe_life_details(rows: list, max_gap_days: int = 7) -> list:
    """Collapse consecutive rows repeating the same phase+sign only days apart.

    /sadhesati_life_details emits one event per sampling step while Saturn sits
    stationary on a sign boundary, so a single ingress arrives as e.g. three identical
    SETTING_START/Aries rows dated 19, 20 and 21 Oct 2027 (the same happens at 14 and
    15 Jan 2079). Keep the first row of each such run. Rows already arrive in ascending
    date order and we never reorder them.
    """
    out: list = []
    for entry in rows:
        key = _entry_key(entry)
        if key is None or not out or _entry_key(out[-1]) != key:
            out.append(entry)
            continue
        prev_date, cur_date = _entry_date(out[-1]), _entry_date(entry)
        if prev_date and cur_date and abs((cur_date - prev_date).days) <= max_gap_days:
            continue  # same event, resampled
        out.append(entry)
    return out


# Progress order of the phases within one 7.5-year cycle. Keys match PHASE_LABELS.
_PHASE_RANK: dict[str, int] = {
    "RISING_START": 0, "RISING_END": 1,
    "PEAK_START": 2, "PEAK_END": 3,
    "SETTING_START": 4, "SETTING_END": 5,
}


def _phase_rank(entry: dict) -> int | None:
    raw = str(entry.get("phase") or entry.get("type") or "").upper()
    return _PHASE_RANK.get(raw)


def mark_retrograde_reentries(rows: list, new_cycle_years: int = 5) -> list:
    """Annotate rows whose phase sequence needs explaining, with the reason why.

    Saturn retrogrades back across a sign boundary and /sadhesati_life_details reports
    every crossing, so the table legitimately shows "Rising Phase Ends" (9-7-2049)
    followed by "Rising Phase Begins" (4-12-2049), and "Setting Phase Ends" (21-5-2086)
    followed by "Setting Phase Begins" (10-11-2086). Both are correct; unannotated they
    look like a sorting bug.

    Sets `retro_reason` to one of:

    - ``"reentry"`` — this row's phase does not advance on the previous row *and* the two
      are close in time, i.e. Saturn crossed back. The time test separates this from the
      start of the next cycle: `SETTING_END` in 2028 followed by `RISING_START` in 2049
      also steps backwards, but 21 years apart it is simply the next Sade Sati.
    - ``"retrograde"`` — the sequence is fine, but the API reports Saturn retrograde at
      this event. Worth stating, though it is not the same claim as a re-entry: saying
      "re-enters after retrograde" on a normally-progressing row would be wrong.
    - ``""`` — nothing to explain.

    Returns shallow copies; `rows` is left alone. Unparseable dates or unknown phase
    enums yield ``""`` rather than a guess.
    """
    out: list = []
    prev: dict | None = None
    for entry in rows:
        if not isinstance(entry, dict):
            out.append(entry)
            continue
        reason = ""
        if prev is not None:
            cur_rank, prev_rank = _phase_rank(entry), _phase_rank(prev)
            cur_date, prev_date = _entry_date(entry), _entry_date(prev)
            if (
                cur_rank is not None and prev_rank is not None
                and cur_rank <= prev_rank
                and cur_date and prev_date
                and (cur_date - prev_date).days < new_cycle_years * 365
            ):
                reason = "reentry"
        if not reason and entry.get("is_saturn_retrograde"):
            reason = "retrograde"
        out.append({**entry, "retro_reason": reason})
        prev = entry
    return out


def _has_data(data: KundliData) -> bool:
    if data.sadhesati_life_details:
        if isinstance(data.sadhesati_life_details, list) and len(data.sadhesati_life_details) > 0:
            return True
        if isinstance(data.sadhesati_life_details, dict) and data.sadhesati_life_details:
            return True
    if data.sadhesati_current_status and isinstance(data.sadhesati_current_status, dict):
        return True
    return False


def render_sade_sati_journey(data: KundliData, lang: str = "en") -> str | None:
    if not _has_data(data):
        return None

    locale = LOCALES.get(lang, LOCALES["en"])

    current_status = {}
    if data.sadhesati_current_status and isinstance(data.sadhesati_current_status, dict):
        current_status = data.sadhesati_current_status

    life_details = []
    if data.sadhesati_life_details:
        if isinstance(data.sadhesati_life_details, list):
            life_details = data.sadhesati_life_details
        elif isinstance(data.sadhesati_life_details, dict):
            inner = data.sadhesati_life_details.get("sadhesati_details")
            if isinstance(inner, list):
                life_details = inner
            else:
                life_details = [data.sadhesati_life_details]
    life_details = mark_retrograde_reentries(dedupe_life_details(life_details))

    remedies_data = None
    if data.sadhesati_remedies:
        remedies_data = data.sadhesati_remedies

    rudraksha = None
    if data.rudraksha_suggestion:
        if isinstance(data.rudraksha_suggestion, dict):
            rudraksha = data.rudraksha_suggestion.get("rudraksha_suggestion", data.rudraksha_suggestion)
        else:
            rudraksha = data.rudraksha_suggestion

    saturn = None
    moon = None
    if data.planets:
        for p in data.planets:
            if p.name == "Saturn":
                saturn = p
            if p.name == "Moon":
                moon = p

    # `is_undergoing_sadhesati` is a prose sentence ("Yes, currently you are undergoing
    # Sadhesati."), so bool() on it is always True — which silently suppressed the
    # "not currently in Sade Sati" reassurance block below. Prefer the real boolean.
    status_flag = current_status.get("sadhesati_status")
    if isinstance(status_flag, bool):
        is_active = status_flag
    else:
        prose = str(current_status.get("is_undergoing_sadhesati") or "").strip().lower()
        is_active = bool(prose) and not prose.startswith("no")

    if lang == "hi":
        current_status = translate_keys(current_status, SADHESATI_KEYS_HI) or {}
    current_status = translate_keys(current_status, STATUS_LABELS.get(lang, STATUS_LABELS["en"])) or {}

    env = make_env()
    template = env.get_template("sade_sati_journey.html")
    return template.render(
        current_status=current_status,
        life_details=life_details,
        remedies_data=remedies_data,
        rudraksha=rudraksha,
        saturn=saturn,
        moon=moon,
        is_active=is_active,
        phase_labels=PHASE_LABELS.get(lang, PHASE_LABELS["en"]),
        narratives=data.narratives,
        locale=locale,
        lang=lang,
    )

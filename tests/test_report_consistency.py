"""Guards against the report contradicting itself.

Each test here pins one defect found by reading a full 70-page live report end to end:
places where the PDF disagreed with itself, printed a raw API enum, repeated a table, or
prescribed two incompatible things in different chapters. They are cheap assertions on
rendered HTML and pure helpers, and they exist because every one of these shipped
invisible to the suite.
"""
from __future__ import annotations

import copy

import pytest

from demo_data import SAMPLE_KUNDLI_DATA
from sections import LOCALES, _safe_time, clock12, fix_api_prose, make_env
from sections.astro_details import render_astro_details
from sections.cover import render_cover
from sections.dosha import _is_empty, _merge_manglik, render_dosha
from sections.life_area_remedies import build_area_remedies
from sections.panchang import render_panchang
from sections.sade_sati_journey import (
    dedupe_life_details,
    mark_retrograde_reentries,
    render_sade_sati_journey,
)


def _life_row(phase: str, sign: str, dmy: str, **extra) -> dict:
    return {"type": phase, "saturn_sign": sign, "date": dmy, **extra}


# --- 1. Birth summary sign labels --------------------------------------------
# /astro_details has no sun-sign field: its `sign`/`SignLord` pair is the Moon's, and so
# are its Naksahtra/Charan. Labelling that row "Sun Sign" printed Aquarius (Saturn) on the
# birth summary while the planet tables correctly showed the Sun in Libra.

def test_astro_details_labels_moon_sign_not_sun_sign() -> None:
    html = render_astro_details(SAMPLE_KUNDLI_DATA, "en")
    assert LOCALES["en"]["moon_sign_janma_rashi"] in html
    assert LOCALES["en"]["ascendant_lord"] in html
    assert "Sun Sign" not in html


# --- 2. Sunrise vs birth-moment panchang -------------------------------------
# The sunrise panchang legitimately differs from the birth-moment one by a step (Yoga
# Vriddhi vs Dhruv). The caption is the only thing stopping that reading as a
# contradiction, so it must survive.

def test_panchang_carries_the_sunrise_reference_note() -> None:
    html = render_panchang(SAMPLE_KUNDLI_DATA, "en")
    assert LOCALES["en"]["sunrise_reference_note"] in html


# --- 3. Manglik verdict ------------------------------------------------------
# /simple_manglik's `is_present` is a severity threshold, so it can say False while
# /manglik reports 15%, LESS_EFFECTIVE and prose saying the dosha *is* present but mild.
# Headlining the bare flag printed "Present: No" directly above "Manglik Dosha is
# present".

def test_merge_manglik_drops_simple_flag_when_detailed_status_exists() -> None:
    merged = _merge_manglik(
        {"is_present": False},
        {"manglik_status": "LESS_EFFECTIVE", "percentage_manglik_present": 15},
    )
    assert "is_present" not in merged
    assert merged["manglik_status"] == "Mild"      # not the raw LESS_EFFECTIVE enum
    assert list(merged)[0] == "manglik_status"     # and it leads the table


def test_merge_manglik_keeps_simple_flag_when_no_detailed_verdict() -> None:
    merged = _merge_manglik({"is_present": True}, None)
    assert merged["is_present"] is True


def test_merge_manglik_translates_status_for_hindi() -> None:
    merged = _merge_manglik(None, {"manglik_status": "LESS_EFFECTIVE"}, "hi")
    assert merged["manglik_status"] == "हल्का"


def test_demo_fixture_exercises_the_live_manglik_shape() -> None:
    """The demo used to carry only `is_manglik`, so /demo never hit the live branch."""
    assert "manglik_status" in SAMPLE_KUNDLI_DATA.manglik
    assert "is_present" in SAMPLE_KUNDLI_DATA.simple_manglik


def test_is_empty_treats_empty_list_as_absent() -> None:
    """`v not in (None, "")` let [] through, printing a heading with no body."""
    assert _is_empty([]) and _is_empty("") and _is_empty(None) and _is_empty({})
    assert not _is_empty(0) and not _is_empty(False) and not _is_empty("x")


# --- 4. Pitra Dosha rule wording ---------------------------------------------
# The API returns rules_matched as the text of the rule it applied, with an "and/or"
# covering alternatives — not a list of combinations found in this chart. "Rules Matched"
# read as an assertion that every named combination was present.

def test_pitra_rules_are_labelled_as_the_applied_rule() -> None:
    data = copy.deepcopy(SAMPLE_KUNDLI_DATA)
    data.pitra_dosha_report = {
        "is_pitri_dosha_present": True,
        "rules_matched": (
            "Conjuction of Moon and Rahu and/or Rahu and Saturn causes Pitri Dosha."
        ),
    }
    html = render_dosha(data, "en")
    assert "Classical Rule Applied" in html
    assert "Rules Matched" not in html


# --- 5. Sade Sati: one table, clearly labelled -------------------------------
# The dedicated sade_sati_journey section renders the same sadhesati_current_status dict
# with natal/transit labelling. The doshas page printed it too, so the identical table
# appeared twice in one report (p31 and p64).

def test_dosha_section_does_not_repeat_the_sadhesati_table() -> None:
    assert SAMPLE_KUNDLI_DATA.sadhesati_current_status, "fixture must supply the data"
    html = render_dosha(SAMPLE_KUNDLI_DATA, "en")
    assert LOCALES["en"]["sadhesati_status_title"] not in html


def test_sade_sati_distinguishes_natal_from_transit() -> None:
    """One natal and one transit value sat under labels that looked identical, directly
    below cards showing natal Saturn — the page read as putting Saturn in two signs."""
    html = render_sade_sati_journey(SAMPLE_KUNDLI_DATA, "en")
    assert LOCALES["en"]["natal_prefix"] in html
    assert "Saturn Now (Transit)" in html
    assert "Natal Moon Sign" in html


# --- 6. Sade Sati cycle table -------------------------------------------------
# /sadhesati_life_details resamples a stationary Saturn sitting on a sign boundary, so one
# ingress arrived as three identical rows dated 19, 20 and 21 Oct 2027.

def test_dedupe_collapses_resampled_ingress() -> None:
    rows = [
        _life_row("SETTING_START", "Aries", "19-10-2027"),
        _life_row("SETTING_START", "Aries", "20-10-2027"),
        _life_row("SETTING_START", "Aries", "21-10-2027"),
        _life_row("SETTING_END", "Aries", "23-2-2028"),
    ]
    assert [r["date"] for r in dedupe_life_details(rows)] == ["19-10-2027", "23-2-2028"]


def test_dedupe_keeps_the_same_phase_and_sign_years_apart() -> None:
    """A repeat in the next cycle is a real event, not a resample."""
    rows = [
        _life_row("RISING_START", "Capricorn", "6-3-2049"),
        _life_row("RISING_START", "Capricorn", "14-1-2079"),
    ]
    assert len(dedupe_life_details(rows)) == 2


# Saturn retrogrades back over a boundary, so "Begins" legitimately follows "Ends".
# Unannotated, that reads as a sorting bug.

def test_retrograde_reentry_is_flagged() -> None:
    rows = mark_retrograde_reentries([
        _life_row("RISING_END", "Capricorn", "9-7-2049"),
        _life_row("RISING_START", "Capricorn", "4-12-2049"),
    ])
    assert rows[1]["retro_reason"] == "reentry"


def test_forward_phase_progression_is_not_flagged() -> None:
    rows = mark_retrograde_reentries([
        _life_row("RISING_START", "Capricorn", "6-3-2049"),
        _life_row("PEAK_START", "Aquarius", "25-2-2052"),
        _life_row("SETTING_START", "Pisces", "20-3-2084"),
    ])
    assert [r["retro_reason"] for r in rows] == ["", "", ""]


def test_next_cycle_is_not_mistaken_for_a_retrograde_reentry() -> None:
    """SETTING_END -> RISING_START steps backwards too; 21 years apart it's a new cycle."""
    rows = mark_retrograde_reentries([
        _life_row("SETTING_END", "Aries", "23-2-2028"),
        _life_row("RISING_START", "Capricorn", "6-3-2049"),
    ])
    assert rows[1]["retro_reason"] == ""


def test_api_retrograde_flag_gets_the_weaker_note_not_a_reentry_claim() -> None:
    """A normally-progressing row must not claim Saturn "re-enters" — it hasn't.

    This is the 9-7-2049 "Rising Phase Ends" row in the live report: retrograde per the
    API, but the phase sequence advances, so only the weaker statement is true.
    """
    rows = mark_retrograde_reentries([
        _life_row("RISING_START", "Capricorn", "6-3-2049"),
        _life_row("RISING_END", "Capricorn", "9-7-2049", is_saturn_retrograde=True),
    ])
    assert rows[1]["retro_reason"] == "retrograde"


def test_a_backwards_step_outranks_the_bare_retrograde_flag() -> None:
    rows = mark_retrograde_reentries([
        _life_row("RISING_END", "Capricorn", "9-7-2049"),
        _life_row("RISING_START", "Capricorn", "4-12-2049", is_saturn_retrograde=True),
    ])
    assert rows[1]["retro_reason"] == "reentry"


def test_mark_retrograde_reentries_does_not_mutate_input() -> None:
    rows = [
        _life_row("RISING_END", "Capricorn", "9-7-2049"),
        _life_row("RISING_START", "Capricorn", "4-12-2049"),
    ]
    mark_retrograde_reentries(rows)
    assert all("retro_reason" not in r for r in rows)


@pytest.mark.parametrize("lang", ["en", "hi"])
def test_both_retrograde_notes_are_localized(lang: str) -> None:
    """Two distinct claims need two distinct strings, or the weaker one lies."""
    assert LOCALES[lang]["ss_retro_note"]
    assert LOCALES[lang]["ss_retrograde_note"]
    assert LOCALES[lang]["ss_retro_note"] != LOCALES[lang]["ss_retrograde_note"]


# --- 7. One gemstone prescription, one chapter -------------------------------
# Stones are prescribed once, in remedy_gemstones. Listing the stone of every significator
# in the life-area blocks told the reader to wear Ruby, Blue Sapphire, Diamond and Red
# Coral on top of the three actually prescribed — Ruby beside Blue Sapphire among them.

def test_area_remedies_do_not_recommend_gemstones() -> None:
    bundles = build_area_remedies(SAMPLE_KUNDLI_DATA, ["Sun", "Saturn", "Venus"], "en")
    assert bundles, "fixture must produce bundles for this to mean anything"
    for bundle in bundles:
        assert "gemstone" not in bundle
    # Mantra / daan / practice must still carry the block.
    assert any(b["mantra"] and b["donation_item"] for b in bundles)


@pytest.mark.parametrize("lang", ["en", "hi"])
def test_area_remedy_gemstone_label_is_gone(lang: str) -> None:
    """Re-adding the row means re-adding the label; fail here first."""
    assert "ar_gemstone" not in LOCALES[lang]


# --- 8. Grammar warts in the API's own prose ---------------------------------

def test_fix_api_prose_corrects_the_karana_typo() -> None:
    out = fix_api_prose(
        "This Karana is said to be exclusively superior for performance marriage "
        "and other auspicious Samskaras of the Brahmanas."
    )
    assert "for performing marriage" in out
    assert "performance marriage" not in out


def test_fix_api_prose_corrects_the_pitra_plural() -> None:
    assert "satisfying 1 rule " in fix_api_prose(
        "Your horoscope is having Pitra Dosha as it is satisfying 1 rules laid down."
    )


@pytest.mark.parametrize(
    "value", ["Rising Phase Begins", "Yellow Sapphire", "", "Aquarius"]
)
def test_fix_api_prose_leaves_ordinary_text_alone(value: str) -> None:
    assert fix_api_prose(value) == value


def test_api_text_filter_is_registered() -> None:
    assert make_env().filters["api_text"] is fix_api_prose


def test_karana_typo_is_corrected_in_the_rendered_panchang() -> None:
    data = copy.deepcopy(SAMPLE_KUNDLI_DATA)
    data.advanced_panchang_sunrise = dict(data.advanced_panchang_sunrise)
    data.advanced_panchang_sunrise["karan"] = {
        "details": {
            "karan_name": "Baalav",
            "special": "Superior for performance marriage and other Samskaras.",
        }
    }
    html = render_panchang(data, "en")
    assert "for performing marriage" in html
    assert "performance marriage" not in html


# --- Bonus: the NaN filter that was eating prose -----------------------------
# The generic render_value macro pipes every scalar through _safe_time in nine templates,
# so a substring "nan" test silently replaced any prose containing fi-nan-ce /
# gover-nan-ce / mainte-nan-ce with an em-dash.

@pytest.mark.parametrize("value", ["finance", "governance", "maintenance", "Dhanishtha"])
def test_safe_time_does_not_blank_prose_containing_nan(value: str) -> None:
    assert _safe_time(value) == value


@pytest.mark.parametrize("value", ["nan", "NaN", "nan:30", "12:nan"])
def test_safe_time_blanks_real_nan_values(value: str) -> None:
    assert _safe_time(value) == "—"


def test_safe_time_still_zero_pads_times() -> None:
    assert _safe_time("6:44:9") == "06:44:09"


# --- 12-hour clock display -----------------------------------------------------
# The report used to print every time in 24-hour form. In the dasha tables that was
# actively ambiguous: "14-5-2005 0:12" gives a reader no way to tell it means just after
# midnight. `clock12` converts the clock-time sites; `_safe_time` deliberately does not
# change, because the generic render_value macro pipes every scalar through it.

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("6:32:30", "6:32 AM"),          # seconds dropped
        ("06:05:42", "6:05 AM"),         # leading zero dropped from the hour
        ("0:12", "12:12 AM"),            # the ambiguous midnight case
        ("12:24", "12:24 PM"),           # noon is PM, not AM
        ("12:00", "12:00 PM"),
        ("23:59", "11:59 PM"),
        ("24:00", "12:00 AM"),           # hour % 24, else this reads as 12:00 PM
        ("17:0", "5:00 PM"),             # single-digit minutes occur in real API data
    ],
)
def test_clock12_converts_bare_clock_times(raw: str, expected: str) -> None:
    assert clock12(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("14-5-1998 6:12", "14-5-1998 6:12 AM"),
        ("14-5-2005 0:12", "14-5-2005 12:12 AM"),
        ("14-5-2023 12:12", "14-5-2023 12:12 PM"),
        ("29-5-2026 6:35", "29-5-2026 6:35 AM"),
        ("1-7-2025 17:0", "1-7-2025 5:00 PM"),   # the row a \d{2} minute regex would drop
    ],
)
def test_clock12_keeps_dates_numeric(raw: str, expected: str) -> None:
    """Dates stay DD-M-YYYY by decision; only the clock part is reformatted."""
    assert clock12(raw) == expected


@pytest.mark.parametrize("raw", ["hello", "Gemini", "What Sade Sati Is: a masterclass",
                                 "finance", "Krishna Tritiya"])
def test_clock12_leaves_non_times_alone(raw: str) -> None:
    assert clock12(raw) == raw


@pytest.mark.parametrize("raw", [None, "", "   ", "nan", "NaN", "NaN:NaN", "NaN:NaN:NaN",
                                 "nan:30"])
def test_clock12_blanks_missing_and_nan_times(raw) -> None:
    """Same guard contract as _safe_time, so a missing sunrise renders alike either way."""
    assert clock12(raw) == "—"


def test_clock12_rejects_impossible_minutes() -> None:
    """Better to show the raw value than silently invent a time."""
    assert clock12("6:75") == "6:75"


def test_clock12_is_registered_but_safe_time_is_unchanged() -> None:
    env = make_env()
    assert env.filters["clock12"] is clock12
    assert env.filters["safe_time"] is _safe_time
    # The 24-hour zero-padder that render_value depends on, pinned in test_pdf_qa too.
    assert _safe_time("17:33:4") == "17:33:04"
    assert _safe_time("6:32:30") == "06:32:30"


def _request_at(hour: int, minute: int):
    req = SAMPLE_KUNDLI_DATA.request.model_copy(update={"hour": hour, "min": minute})
    return SAMPLE_KUNDLI_DATA.model_copy(update={"request": req})


@pytest.mark.parametrize(
    ("hour", "minute", "expected"),
    [(12, 24, "12:24 PM"), (0, 12, "12:12 AM"), (13, 5, "1:05 PM"), (9, 0, "9:00 AM")],
)
def test_cover_prints_birth_time_in_12_hour(hour: int, minute: int, expected: str) -> None:
    """The two boundary cases a naive `hour % 12` gets wrong are noon and midnight."""
    assert expected in render_cover(_request_at(hour, minute), "en")


def test_panchang_times_carry_a_meridiem_marker() -> None:
    html = render_panchang(SAMPLE_KUNDLI_DATA, "en")
    assert "AM" in html or "PM" in html
    # Proves the filter is wired at the sunrise cell, not merely defined: the fixture's
    # sunrise is 06:05:42 and must no longer appear in 24-hour form.
    assert "06:05:42" not in html

"""Tests for per-request brand selection (Batraa default, Bloomx alternative).

The load-bearing property is isolation: no asset, URL or phone number belonging to one
brand may appear in the other's report.
"""
from __future__ import annotations

import dataclasses
import pathlib

import pytest

from branding import BATRAA, BATRAA_ONLY_SECTIONS, BLOOMX, Brand, brand_for, get_brand
from config import settings
from models import KundliRequest

TEMPLATES_IMAGES = pathlib.Path(__file__).parent.parent / "templates" / "images"

BATRAA_MARKERS = (
    "front_page.jpg", "kundli_logo.png", "btr_image.JPG",
    "batraa", "Batraa", "thebatraanumerology",
)
BLOOMX_MARKERS = ("bloomx", "Bloomx", "bloomxsolutions")


def _values(brand: Brand) -> str:
    """Every field flattened to one string, for substring-leak assertions."""
    return " ".join(str(v) for v in dataclasses.asdict(brand).values())


# --- resolution -------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("bloomx", BLOOMX),
    ("BLOOMX", BLOOMX),
    ("  Bloomx  ", BLOOMX),
    ("batraa", BATRAA),
    ("BATRAA", BATRAA),
    ("", BATRAA),
    (None, BATRAA),
    ("nonsense", BATRAA),
    ("bloom", BATRAA),        # near-miss must not resolve to bloomx
    ("bloomx-kundli", BATRAA),
])
def test_get_brand_resolution(raw, expected) -> None:
    assert get_brand(raw).key == expected


def test_get_brand_never_raises() -> None:
    """An unknown value must not fail a render — sheet_worker parks failures as
    permanent, so a brand typo could otherwise strand a paid order."""
    for raw in [None, "", "   ", "?!", "123", "bloomx\n", "\tbatraa"]:
        assert get_brand(raw).key in {BATRAA, BLOOMX}


def test_brand_for_reads_the_request() -> None:
    req = KundliRequest(day=1, month=1, year=2000, hour=1, min=1,
                        lat=1.0, lon=1.0, tzone=5.5, kundli_type="bloomx")
    data = type("D", (), {"request": req})()
    assert brand_for(data).key == BLOOMX


def test_brand_for_tolerates_missing_request() -> None:
    """Defensive: incomplete doubles must fall back, not AttributeError."""
    assert brand_for(object()).key == BATRAA
    assert brand_for(None).key == BATRAA


def test_kundli_request_defaults_to_batraa() -> None:
    req = KundliRequest(day=1, month=1, year=2000, hour=1, min=1,
                        lat=1.0, lon=1.0, tzone=5.5)
    assert req.kundli_type == "batraa"
    assert brand_for(type("D", (), {"request": req})()).key == BATRAA


# --- the default brand is unchanged ----------------------------------------

def test_batraa_mirrors_current_settings() -> None:
    """Regression guard: the default report must keep using today's settings."""
    b = get_brand("batraa")
    assert b.author_name == settings.author_name
    assert b.author_title == settings.author_title
    assert b.cta_consult_url == settings.cta_consult_url
    assert b.cta_pooja_url == settings.cta_pooja_url
    assert b.cta_rudraksha_url == settings.cta_rudraksha_url
    assert b.footer_enabled == settings.brand_footer_enabled
    assert b.footer_name == settings.brand_footer_name
    assert b.footer_url == settings.brand_footer_url
    assert b.footer_phone == settings.brand_footer_phone
    assert b.front_page_image == "front_page.jpg"
    assert b.logo_image == "kundli_logo.png"
    assert b.filler_images == ("btr_image.JPG",)


def test_brand_reads_settings_at_call_time(monkeypatch) -> None:
    """Not frozen at import — otherwise monkeypatching settings in tests, and .env
    changes in deployment, would silently not apply."""
    monkeypatch.setattr(settings, "brand_footer_phone", "+91-0000000000")
    assert get_brand("batraa").footer_phone == "+91-0000000000"

    monkeypatch.setattr(settings, "bloomx_brand_footer_phone", "+91-1111111111")
    assert get_brand("bloomx").footer_phone == "+91-1111111111"


# --- isolation, both directions --------------------------------------------

def test_bloomx_carries_no_batraa_marker() -> None:
    blob = _values(get_brand("bloomx"))
    leaked = [m for m in BATRAA_MARKERS if m in blob]
    assert not leaked, f"Batraa markers leaked into the Bloomx brand: {leaked}"


def test_batraa_carries_no_bloomx_marker() -> None:
    blob = _values(get_brand("batraa"))
    leaked = [m for m in BLOOMX_MARKERS if m in blob]
    assert not leaked, f"Bloomx markers leaked into the Batraa brand: {leaked}"


def test_brands_differ_on_every_visible_surface() -> None:
    a, b = get_brand("batraa"), get_brand("bloomx")
    assert a.front_page_image != b.front_page_image
    assert a.logo_image != b.logo_image
    assert a.logo_alt != b.logo_alt
    assert a.footer_url != b.footer_url
    assert a.footer_phone != b.footer_phone
    assert a.filler_images != b.filler_images


def test_bloomx_has_no_filler_art() -> None:
    """Bloomx ships no promo image, so the filler pass must be a no-op rather than
    stamping Batraa art onto a Bloomx report."""
    assert get_brand("bloomx").filler_images == ()


def test_bloomx_shows_the_pooja_card() -> None:
    assert get_brand("bloomx").cta_pooja_url


# --- the assets actually exist ---------------------------------------------

@pytest.mark.parametrize("key", [BATRAA, BLOOMX])
def test_brand_images_exist_on_disk(key) -> None:
    brand = get_brand(key)
    for name in (brand.front_page_image, brand.logo_image, *brand.filler_images):
        assert (TEMPLATES_IMAGES / name).exists(), f"{key}: missing {name}"


# --- Batraa-only pages ------------------------------------------------------

def test_batraa_only_sections_are_image_only_sections() -> None:
    """Both are artwork pages, so they must also honour PDF_IMAGES_ENABLED."""
    from pdf_generator import IMAGE_ONLY_SECTIONS
    assert BATRAA_ONLY_SECTIONS <= IMAGE_ONLY_SECTIONS


def test_batraa_only_sections_are_never_toc_chapters() -> None:
    """Skipping them for Bloomx must not be able to change the TOC."""
    from sections import TOC_CHAPTERS
    members = {m for _, ms in TOC_CHAPTERS for m in ms}
    assert not (BATRAA_ONLY_SECTIONS & members)


def test_batraa_only_sections_exist_in_section_renderers() -> None:
    from pdf_generator import SECTION_RENDERERS
    names = {n for n, _ in SECTION_RENDERERS}
    assert BATRAA_ONLY_SECTIONS <= names

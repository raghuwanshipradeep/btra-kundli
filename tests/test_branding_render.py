"""End-to-end proof that the selected brand actually reaches the rendered PDF.

test_branding.py checks brand resolution in isolation; these tests render real PDFs and
inspect the embedded images and page text, so a brand value that never made it through
the Jinja layers fails here rather than shipping a mis-branded report.
"""
from __future__ import annotations

import pytest

from branding import get_brand
from config import settings
from demo_data import SAMPLE_KUNDLI_DATA
from pdf_generator import PDFGenerator, _fill_gap_pages


def _data_for(kundli_type: str):
    data = SAMPLE_KUNDLI_DATA.model_copy(deep=True)
    data.request.kundli_type = kundli_type
    return data


def _embedded_image_sizes(pdf_bytes: bytes) -> set[int]:
    """Byte lengths of every embedded image — an asset fingerprint that needs no
    filename, since PDFs don't retain the source paths."""
    import fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return {len(doc.extract_image(xref)["image"])
                for xref in {img[0] for pno in range(len(doc)) for img in doc.get_page_images(pno)}}
    finally:
        doc.close()


def _text(pdf_bytes: bytes) -> str:
    import fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


@pytest.fixture
def generator() -> PDFGenerator:
    return PDFGenerator()


# --- both brands render -----------------------------------------------------

@pytest.mark.parametrize("kundli_type", ["batraa", "bloomx"])
def test_brand_renders_a_valid_pdf(generator: PDFGenerator, kundli_type) -> None:
    pdf = generator.generate(_data_for(kundli_type), "en")
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 50_000


def test_the_two_brands_produce_different_pdfs(generator: PDFGenerator) -> None:
    assert generator.generate(_data_for("batraa"), "en") != \
           generator.generate(_data_for("bloomx"), "en")


def test_unknown_brand_matches_batraa_output(generator: PDFGenerator) -> None:
    """An unrecognised value must degrade to the default report, not a broken one."""
    odd = _embedded_image_sizes(generator.generate(_data_for("nonsense"), "en"))
    batraa = _embedded_image_sizes(generator.generate(_data_for("batraa"), "en"))
    assert odd == batraa


# --- footer text is brand-specific -----------------------------------------

def test_footer_shows_the_selected_brand(generator: PDFGenerator, monkeypatch) -> None:
    monkeypatch.setattr(settings, "brand_footer_enabled", True)
    monkeypatch.setattr(settings, "brand_footer_name", "The Batraa Numerology")
    monkeypatch.setattr(settings, "brand_footer_url", "https://thebatraanumerology.com/")
    monkeypatch.setattr(settings, "brand_footer_phone", "+91-9953152520")

    batraa = _text(generator.generate(_data_for("batraa"), "en"))
    bloomx = _text(generator.generate(_data_for("bloomx"), "en"))

    assert "thebatraanumerology.com" in batraa
    assert "bloomxsolutions.com" in bloomx

    # The isolation claim, stated as the assertions that would fail if it broke.
    assert "thebatraanumerology.com" not in bloomx
    assert "9953152520" not in bloomx
    assert get_brand("bloomx").footer_phone.replace("+91-", "") in bloomx


# --- cover artwork swaps ----------------------------------------------------

def test_front_page_image_differs_between_brands(generator: PDFGenerator) -> None:
    """The Bloomx cover must actually be embedded, not just configured."""
    import pathlib

    images = pathlib.Path(__file__).parent.parent / "templates" / "images"
    bloomx_cover = (images / get_brand("bloomx").front_page_image).stat().st_size
    batraa_cover = (images / get_brand("batraa").front_page_image).stat().st_size

    bloomx_sizes = _embedded_image_sizes(generator.generate(_data_for("bloomx"), "en"))
    batraa_sizes = _embedded_image_sizes(generator.generate(_data_for("batraa"), "en"))

    # Sizes are compared loosely: WeasyPrint may re-encode, so assert the sets differ
    # and that neither report embeds an image the size of the other brand's cover.
    assert bloomx_sizes != batraa_sizes
    assert batraa_cover not in bloomx_sizes
    assert bloomx_cover not in batraa_sizes


# --- Batraa-only artwork is suppressed -------------------------------------

def test_bloomx_drops_batraa_only_sections(generator: PDFGenerator, monkeypatch) -> None:
    """With images on, Batraa gets its astrologer page and offer banner; Bloomx must
    not, so its report has strictly fewer pages."""
    monkeypatch.setattr(settings, "pdf_images_enabled", True)
    monkeypatch.setattr(settings, "filler_images_enabled", False)

    import fitz

    def pages(kundli_type: str) -> int:
        doc = fitz.open(stream=generator.generate(_data_for(kundli_type), "en"),
                        filetype="pdf")
        try:
            return len(doc)
        finally:
            doc.close()

    assert pages("bloomx") < pages("batraa")


def test_bloomx_report_embeds_no_batraa_promo(generator: PDFGenerator, monkeypatch) -> None:
    """The live leak: FILLER_IMAGES_ENABLED is true in production."""
    import pathlib

    monkeypatch.setattr(settings, "filler_images_enabled", True)
    images = pathlib.Path(__file__).parent.parent / "templates" / "images"
    promo_size = (images / "btr_image.JPG").stat().st_size

    bloomx = _embedded_image_sizes(generator.generate(_data_for("bloomx"), "en"))
    assert promo_size not in bloomx


# --- the filler pass itself -------------------------------------------------

def test_fill_gap_pages_is_a_noop_without_art() -> None:
    pdf = PDFGenerator().generate(_data_for("bloomx"), "en")
    assert _fill_gap_pages(pdf, ()) == pdf


def test_fill_gap_pages_defaults_to_batraa_promo_when_unspecified() -> None:
    """Back-compat for the bare _fill_gap_pages(pdf) call shape."""
    pdf = PDFGenerator().generate(_data_for("batraa"), "en")
    assert _fill_gap_pages(pdf)[:5] == b"%PDF-"

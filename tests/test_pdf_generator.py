from __future__ import annotations

import pytest

from demo_data import SAMPLE_KUNDLI_DATA
from pdf_generator import PDFGenerator


@pytest.fixture
def generator() -> PDFGenerator:
    return PDFGenerator()


def test_pdf_generated_and_valid(generator: PDFGenerator) -> None:
    pdf = generator.generate(SAMPLE_KUNDLI_DATA, "en")
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 50_000


def test_pdf_hindi_output(generator: PDFGenerator) -> None:
    pdf = generator.generate(SAMPLE_KUNDLI_DATA, "hi")
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 50_000


def test_pdf_with_subset_sections(generator: PDFGenerator) -> None:
    pdf = generator.generate(
        SAMPLE_KUNDLI_DATA, "en",
        include_sections=["cover", "planets"],
    )
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 10_000


def test_pdf_with_empty_data(generator: PDFGenerator) -> None:
    from models import KundliData, KundliRequest

    empty_data = KundliData(
        request=KundliRequest(
            name="Empty", day=1, month=1, year=2000,
            hour=0, min=0, lat=0.0, lon=0.0, tzone=0.0,
        )
    )
    pdf = generator.generate(empty_data, "en")
    assert pdf[:5] == b"%PDF-"


TESTABLE_SECTIONS = [
    "outer_planets",
    "three_pillars",
    "sade_sati_journey",
    "raj_yoga_celebration",
    "mahadasha_journey",
    "numerology_personality",
    "remedy_rudraksha",
    "remedy_gemstones",
    "remedy_mantras",
    "remedy_ishta_devata",
    "remedy_yantra",
    "remedy_daan",
    "love_marriage",
    "career_path",
    "rahu_ketu_analysis",
    "spiritual_potential",
    "marriage_timing",
    "material_comforts",
]


@pytest.mark.parametrize("section_name", TESTABLE_SECTIONS)
def test_section_renders_without_error(generator: PDFGenerator, section_name: str) -> None:
    pdf = generator.generate(SAMPLE_KUNDLI_DATA, "en", [section_name])
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000


@pytest.mark.parametrize("section_name", TESTABLE_SECTIONS)
def test_section_renders_hindi(generator: PDFGenerator, section_name: str) -> None:
    pdf = generator.generate(SAMPLE_KUNDLI_DATA, "hi", [section_name])
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000


def test_authors_note_skips_without_config() -> None:
    from sections.authors_note import render_authors_note
    result = render_authors_note(SAMPLE_KUNDLI_DATA, "en")
    assert result is None


def test_closing_cta_skips_without_config() -> None:
    from sections.closing_cta import render_closing_cta
    result = render_closing_cta(SAMPLE_KUNDLI_DATA, "en")
    assert result is None

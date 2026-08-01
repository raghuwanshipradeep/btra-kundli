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
    "three_pillars",
    "sade_sati_journey",
    "mahadasha_journey",
    "numerology_personality",
    "remedy_rudraksha",
    "remedy_gemstones",
    "remedy_mantras",
    "remedy_yantra",
    "remedy_daan",
    "career_path",
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


# Both renderers read the module-level `config.settings` singleton, which is populated from
# the developer's real .env. Without patching, these tests assert "no AUTHOR_NAME configured"
# on a machine where AUTHOR_NAME *is* configured, so they pass only against an empty .env.
# Patching the attribute makes each test assert its own branch either way.


def test_authors_note_skips_without_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from config import settings
    from sections.authors_note import render_authors_note

    monkeypatch.setattr(settings, "author_name", "")
    assert render_authors_note(SAMPLE_KUNDLI_DATA, "en") is None


def test_authors_note_renders_with_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """AUTHOR_NAME is a gate, not content: templates/authors_note.html is an image-based
    page and does not print the name. So this asserts the section appears, nothing more."""
    from config import settings
    from sections.authors_note import render_authors_note

    monkeypatch.setattr(settings, "author_name", "Pandit Test")
    monkeypatch.setattr(settings, "author_title", "Jyotish Acharya")

    result = render_authors_note(SAMPLE_KUNDLI_DATA, "en")
    assert result is not None
    assert "authors-note-page" in result


def test_closing_cta_skips_without_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from config import settings
    from sections.closing_cta import render_closing_cta

    monkeypatch.setattr(settings, "cta_consult_url", "")
    monkeypatch.setattr(settings, "cta_pooja_url", "")
    monkeypatch.setattr(settings, "cta_rudraksha_url", "")
    assert render_closing_cta(SAMPLE_KUNDLI_DATA, "en") is None


@pytest.mark.parametrize("field", ["cta_consult_url", "cta_pooja_url", "cta_rudraksha_url"])
def test_closing_cta_renders_with_any_single_url(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Any one URL alone is enough — the renderer's guard is an `and` over the absences."""
    from config import settings
    from sections.closing_cta import render_closing_cta

    for f in ("cta_consult_url", "cta_pooja_url", "cta_rudraksha_url"):
        monkeypatch.setattr(settings, f, "")
    monkeypatch.setattr(settings, field, "https://example.test/x")
    assert render_closing_cta(SAMPLE_KUNDLI_DATA, "en") is not None

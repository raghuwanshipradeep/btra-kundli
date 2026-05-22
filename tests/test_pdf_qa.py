"""Regression tests for QA issues found in generated Kundli PDFs."""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import pytest

from demo_data import SAMPLE_KUNDLI_DATA
from pdf_generator import PDFGenerator
from sections import _safe_time, format_indian_datetime


def _pdf_to_text(pdf_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        path = f.name
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", path, "-"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            pytest.skip("pdftotext not available")
        return result.stdout
    except FileNotFoundError:
        pytest.skip("pdftotext not installed (poppler-utils required)")
    finally:
        Path(path).unlink(missing_ok=True)


@pytest.fixture
def generator() -> PDFGenerator:
    return PDFGenerator()


@pytest.fixture
def en_pdf(generator: PDFGenerator) -> bytes:
    return generator.generate(SAMPLE_KUNDLI_DATA, "en")


@pytest.fixture
def hi_pdf(generator: PDFGenerator) -> bytes:
    return generator.generate(SAMPLE_KUNDLI_DATA, "hi")


class TestP01DashaDict:
    def test_no_raw_dict_repr_in_pdf(self, en_pdf: bytes) -> None:
        text = _pdf_to_text(en_pdf)
        for token in ["'planet':", "'planet_id':", "'dasha_period':", "{'planet'"]:
            assert token not in text, f"Raw dict leaked: {token}"


class TestP05NaN:
    def test_no_nan_in_pdf(self, en_pdf: bytes) -> None:
        text = _pdf_to_text(en_pdf)
        assert "NaN" not in text
        assert not re.search(r"\bNone\b", text)
        assert "undefined" not in text


class TestP07TimeFormat:
    def test_time_format_zero_padded(self, en_pdf: bytes) -> None:
        text = _pdf_to_text(en_pdf)
        bad = re.findall(r"\b\d{1,2}:\d{1,2}:\d\b(?!\d)", text)
        assert len(bad) == 0, f"Unpadded times found: {bad[:5]}"


class TestP03ChartCaption:
    def test_natal_wheel_label_used(self, en_pdf: bytes) -> None:
        text = _pdf_to_text(en_pdf)
        assert "Natal Wheel" in text

    def test_hindi_caption_updated_in_locale(self) -> None:
        from sections import LOCALES
        assert "नैटल व्हील" in LOCALES["hi"]["chart_caption"]
        assert "उत्तर भारतीय शैली" not in LOCALES["hi"]["chart_caption"]


class TestSafeTimeFilter:
    def test_none_returns_dash(self) -> None:
        assert _safe_time(None) == "—"

    def test_nan_returns_dash(self) -> None:
        assert _safe_time("NaN") == "—"
        assert _safe_time("NaN:NaN:NaN") == "—"

    def test_empty_returns_dash(self) -> None:
        assert _safe_time("") == "—"

    def test_zero_pads_time(self) -> None:
        assert _safe_time("17:33:4") == "17:33:04"
        assert _safe_time("6:5:2") == "06:05:02"

    def test_already_padded_unchanged(self) -> None:
        assert _safe_time("06:05:42") == "06:05:42"

    def test_non_time_passthrough(self) -> None:
        assert _safe_time("hello") == "hello"


class TestIndianDateFormat:
    def test_english_format(self) -> None:
        result = format_indian_datetime("6-6-1984 19:34", "en")
        assert result == "06 June 1984, 7:34 PM"

    def test_hindi_format(self) -> None:
        result = format_indian_datetime("6-6-1984 19:34", "hi")
        assert result == "06 जून 1984, 7:34 PM"

    def test_date_only(self) -> None:
        result = format_indian_datetime("16-8-2012", "en")
        assert result == "16 August 2012"

    def test_invalid_passthrough(self) -> None:
        assert format_indian_datetime("not-a-date") == "not-a-date"

    def test_none_returns_empty(self) -> None:
        assert format_indian_datetime(None) == ""

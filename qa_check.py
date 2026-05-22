"""Standalone QA checker for generated Kundli PDFs.

Usage:
    python qa_check.py demo.pdf
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path


def pdf_to_text(pdf_path: str) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        print(f"ERROR: pdftotext failed: {result.stderr}")
        sys.exit(2)
    return result.stdout


def check_no_raw_dict(text: str) -> list[str]:
    errors = []
    for token in ["'planet':", "'planet_id':", "'dasha_period':", "{'planet'"]:
        if token in text:
            errors.append(f"P0-1 FAIL: Raw dict leaked: {token}")
    return errors


def check_no_nan(text: str) -> list[str]:
    errors = []
    if "NaN" in text:
        errors.append("P0-5 FAIL: 'NaN' found in PDF text")
    if re.search(r"\bNone\b", text):
        errors.append("P0-5 FAIL: 'None' found in PDF text")
    return errors


def check_time_format(text: str) -> list[str]:
    bad = re.findall(r"\b\d{1,2}:\d{1,2}:\d\b(?!\d)", text)
    if bad:
        return [f"P0-7 FAIL: Unpadded times found: {bad[:5]}"]
    return []


def check_chart_caption(text: str) -> list[str]:
    errors = []
    if "North Indian Style" in text:
        errors.append("P0-3 FAIL: 'North Indian Style' caption on Western wheel chart")
    if "उत्तर भारतीय शैली" in text:
        errors.append("P0-3 FAIL: Hindi 'North Indian Style' caption on Western wheel chart")
    return errors


def check_no_internal_values(text: str) -> list[str]:
    errors = []
    if "planet_small" in text:
        errors.append("P1-10 FAIL: 'planet_small' internal field visible")
    return errors


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python qa_check.py <pdf_file>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    print(f"Checking {pdf_path}...")
    text = pdf_to_text(pdf_path)
    print(f"Extracted {len(text)} characters from PDF")

    all_errors: list[str] = []
    all_errors.extend(check_no_raw_dict(text))
    all_errors.extend(check_no_nan(text))
    all_errors.extend(check_time_format(text))
    all_errors.extend(check_chart_caption(text))
    all_errors.extend(check_no_internal_values(text))

    if all_errors:
        print(f"\nFAILED — {len(all_errors)} issue(s):")
        for err in all_errors:
            print(f"  {err}")
        sys.exit(1)
    else:
        print("\nPASSED — All QA checks OK")


if __name__ == "__main__":
    main()

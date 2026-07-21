"""Shared kundli-generation pipeline, extracted from main.py so both the FastAPI web
app and the standalone sheet sweeper (run_sweeper.py) reuse it WITHOUT importing the
FastAPI ``app`` — importing main would boot the web app inside the sweeper process and
risk a circular import. Behavior is identical to the code that previously lived in main.py.
"""
from __future__ import annotations

import asyncio
import logging
import pathlib

from fastapi import HTTPException

from api_client import AstrologyAPIClient
from config import settings
from models import KundliRequest
from narrative_engine import generate_narratives, translate_reports
from pdf_generator import PDFGenerator

logger = logging.getLogger(__name__)

pdf_gen = PDFGenerator()

# Gate on concurrent PDF generations. A burst of simultaneous paid orders would
# otherwise all start at once, starve the shared AstrologyAPI Semaphore(10), and
# blow past the per-job timeout wall (only a handful finishing). This caps how
# many render concurrently; the rest queue and complete moments later. Lazily
# created on the running loop so tests importing this module don't bind a loop.
_GENERATION_SLOTS: asyncio.Semaphore | None = None


def _get_generation_slots() -> asyncio.Semaphore:
    global _GENERATION_SLOTS
    if _GENERATION_SLOTS is None:
        _GENERATION_SLOTS = asyncio.Semaphore(settings.generation_concurrency)
    return _GENERATION_SLOTS


def _save_recovery_pdf(order_id: str, filename: str, pdf_bytes: bytes) -> str | None:
    """Persist a paid PDF to disk when the Drive upload failed, so it's
    recoverable instead of lost. Returns the path written, or None if disabled
    or the write itself failed (already-bad situation — never raise)."""
    if not settings.drive_recovery_dir:
        return None
    try:
        recovery_dir = pathlib.Path(settings.drive_recovery_dir)
        recovery_dir.mkdir(parents=True, exist_ok=True)
        # Prefix with order_id so the file is unambiguous and collision-free.
        dest = recovery_dir / f"{order_id}__{filename}"
        dest.write_bytes(pdf_bytes)
        return str(dest)
    except OSError:
        logger.exception("Failed to write recovery PDF for order=%s", order_id)
        return None


async def _build_kundli_pdf(request: KundliRequest, order_id: str = "") -> tuple[bytes, str]:
    """Run the full pipeline: fetch astrology data, narrate, translate, render PDF.
    Returns (pdf_bytes, filename). This is where the PAID API calls happen.
    """
    try:
        async with AstrologyAPIClient(lang=request.lang) as client:
            kundli_data = await client.fetch_all(request)
    except Exception:
        logger.exception("API fetch failed")
        raise HTTPException(status_code=502, detail="Failed to fetch astrology data")

    try:
        kundli_data.narratives = await generate_narratives(kundli_data, request.lang)
    except Exception:
        logger.exception("Narrative generation failed, proceeding without narratives")
        kundli_data.narratives = {}

    try:
        await translate_reports(kundli_data, request.lang)
    except Exception:
        logger.exception("Report translation failed, proceeding with English text")

    try:
        pdf_bytes = await asyncio.to_thread(
            pdf_gen.generate, kundli_data, request.lang,
            report_tier=request.report_tier,
        )
    except Exception:
        logger.exception("PDF generation failed")
        raise HTTPException(status_code=500, detail="PDF generation failed")

    filename = _build_filename(request, order_id)
    return pdf_bytes, filename


def _build_filename(request: KundliRequest, order_id: str = "") -> str:
    """Build the archive filename as First##Phone##Email##OrderId.pdf.

    Only the first name word is used (e.g. "Pradeep Raghuwanshi" -> "Pradeep"),
    then phone, email, and the order id are appended with '##'. Empty fields
    are skipped (e.g. the free/dev flow has no order id).
    """
    def _clean(value: str) -> str:
        return "".join(c for c in value if c.isalnum() or c in "@._-").strip()

    name_parts = [_clean(w) for w in request.name.split() if _clean(w)]
    first_name = name_parts[0] if name_parts else ""
    parts = [first_name, _clean(request.phone), _clean(request.email), _clean(order_id)]
    base = "##".join(p for p in parts if p) or "kundli"
    return f"{base}.pdf"

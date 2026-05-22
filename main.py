from __future__ import annotations

import asyncio
import logging
import pathlib
from io import BytesIO

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from api_client import AstrologyAPIClient
from config import settings
from models import KundliRequest, MatchRequest
from narrative_engine import generate_narratives, translate_reports
from pdf_generator import PDFGenerator
from match_pdf_generator import MatchPDFGenerator

STATIC_DIR = pathlib.Path(__file__).parent / "static"

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("weasyprint").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Kundli", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
pdf_gen = PDFGenerator()
match_pdf_gen = MatchPDFGenerator()


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/geo-search")
async def geo_search(place: str = Query(..., min_length=2)):
    async with AstrologyAPIClient() as client:
        results = await client.get_geo_details(place)
    if results is None:
        return {"geonames": []}
    return {"geonames": [r.model_dump() for r in results]}


@app.get("/api/timezone")
async def timezone_lookup(
    day: int = 1,
    month: int = 1,
    year: int = 2000,
    hour: int = 12,
    min: int = 0,
    lat: float = 0.0,
    lon: float = 0.0,
    tzone: float = 5.5,
):
    payload = {
        "day": day, "month": month, "year": year,
        "hour": hour, "min": min,
        "lat": lat, "lon": lon, "tzone": tzone,
    }
    async with AstrologyAPIClient() as client:
        result = await client.get_timezone_with_dst(payload)
    if result is None:
        return {"timezone": tzone}
    return result


@app.post("/generate-kundli")
async def generate_kundli(request: KundliRequest) -> StreamingResponse:
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

    safe_name = "".join(c for c in request.name if c.isalnum() or c in " _-").strip()
    filename = f"kundli_{safe_name}_{request.year}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@app.post("/generate-match")
async def generate_match(request: MatchRequest) -> StreamingResponse:
    try:
        async with AstrologyAPIClient(lang=request.lang) as client:
            match_data = await client.fetch_match(request)
    except Exception:
        logger.exception("Match API fetch failed")
        raise HTTPException(status_code=502, detail="Failed to fetch match data")

    try:
        pdf_bytes = await asyncio.to_thread(
            match_pdf_gen.generate, match_data, request.lang
        )
    except Exception:
        logger.exception("Match PDF generation failed")
        raise HTTPException(status_code=500, detail="Match PDF generation failed")

    safe_m = "".join(c for c in request.m_name if c.isalnum() or c in " _-").strip()
    safe_f = "".join(c for c in request.f_name if c.isalnum() or c in " _-").strip()
    filename = f"match_{safe_m}_{safe_f}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@app.get("/demo")
async def demo() -> StreamingResponse:
    from demo_data import SAMPLE_KUNDLI_DATA

    data = SAMPLE_KUNDLI_DATA.model_copy(deep=True)
    try:
        data.narratives = await generate_narratives(data, "en")
    except Exception:
        logger.exception("Demo narrative generation failed")
        data.narratives = {}

    try:
        await translate_reports(data, "en")
    except Exception:
        logger.exception("Demo translation failed")

    try:
        pdf_bytes = await asyncio.to_thread(
            pdf_gen.generate, data, "en"
        )
    except Exception:
        logger.exception("Demo PDF generation failed")
        raise HTTPException(status_code=500, detail="Demo PDF generation failed")

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="demo_kundli.pdf"'},
    )

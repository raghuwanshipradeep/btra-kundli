from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import pathlib
import time
from io import BytesIO

import razorpay
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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


# ---------------------------------------------------------------------------
# Razorpay client (lazy init so missing keys don't crash startup)
# ---------------------------------------------------------------------------
_razorpay_client: razorpay.Client | None = None


def _get_razorpay_client() -> razorpay.Client:
    global _razorpay_client
    if _razorpay_client is None:
        if not settings.razorpay_key_id or not settings.razorpay_key_secret:
            raise HTTPException(status_code=503, detail="Payment not configured")
        _razorpay_client = razorpay.Client(
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
        )
    return _razorpay_client


# ---------------------------------------------------------------------------
# Order store: order_id -> (KundliRequest, created_at)
# Production should use Redis or the existing aiosqlite DB.
# ---------------------------------------------------------------------------
_ORDER_STORE: dict[str, tuple[KundliRequest, float]] = {}
_ORDER_TTL_SECONDS = 30 * 60


def _store_order(order_id: str, request: KundliRequest) -> None:
    _prune_orders()
    _ORDER_STORE[order_id] = (request, time.time())


def _get_order(order_id: str) -> KundliRequest | None:
    entry = _ORDER_STORE.get(order_id)
    if not entry:
        return None
    request, created = entry
    if time.time() - created > _ORDER_TTL_SECONDS:
        _ORDER_STORE.pop(order_id, None)
        return None
    return request


def _prune_orders() -> None:
    now = time.time()
    expired = [k for k, (_, t) in _ORDER_STORE.items() if now - t > _ORDER_TTL_SECONDS]
    for k in expired:
        _ORDER_STORE.pop(k, None)


# ---------------------------------------------------------------------------
# Reusable PDF pipeline
# ---------------------------------------------------------------------------
async def _build_kundli_pdf(request: KundliRequest) -> tuple[bytes, str]:
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

    safe_name = "".join(c for c in request.name if c.isalnum() or c in " _-").strip()
    filename = f"kundli_{safe_name}_{request.year}.pdf"
    return pdf_bytes, filename


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------
def _verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    message = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(
        settings.razorpay_key_secret.encode(),
        message,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


class PaymentVerification(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
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


@app.get("/api/payment-config")
async def payment_config() -> dict:
    """Return whether payment is enabled and the price, so the frontend can adapt."""
    enabled = bool(settings.razorpay_key_id and settings.razorpay_key_secret)
    return {
        "enabled": enabled,
        "amount": settings.kundli_price_paise,
        "currency": settings.payment_currency,
    }


@app.post("/create-order")
async def create_order(request: KundliRequest) -> dict:
    if not request.lat or not request.lon:
        raise HTTPException(status_code=400, detail="Place not selected")

    client = _get_razorpay_client()
    try:
        order = await asyncio.to_thread(
            client.order.create,
            {
                "amount": settings.kundli_price_paise,
                "currency": settings.payment_currency,
                "receipt": f"kundli_{int(time.time())}",
                "notes": {"name": request.name, "year": str(request.year)},
            },
        )
    except Exception:
        logger.exception("Razorpay order creation failed")
        raise HTTPException(status_code=502, detail="Could not create payment order")

    _store_order(order["id"], request)

    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key_id": settings.razorpay_key_id,
        "name": request.name,
    }


@app.post("/verify-and-generate")
async def verify_and_generate(verification: PaymentVerification) -> StreamingResponse:
    if not _verify_signature(
        verification.razorpay_order_id,
        verification.razorpay_payment_id,
        verification.razorpay_signature,
    ):
        logger.warning("Invalid payment signature for order %s", verification.razorpay_order_id)
        raise HTTPException(status_code=400, detail="Payment verification failed")

    request = _get_order(verification.razorpay_order_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Order not found or expired")

    try:
        client = _get_razorpay_client()
        payment = await asyncio.to_thread(client.payment.fetch, verification.razorpay_payment_id)
        if payment.get("status") not in ("captured", "authorized"):
            raise HTTPException(status_code=400, detail="Payment not completed")
        if payment.get("amount") != settings.kundli_price_paise:
            logger.warning("Amount mismatch on order %s", verification.razorpay_order_id)
            raise HTTPException(status_code=400, detail="Payment amount mismatch")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Payment fetch failed")
        raise HTTPException(status_code=502, detail="Could not confirm payment")

    pdf_bytes, filename = await _build_kundli_pdf(request)

    _ORDER_STORE.pop(verification.razorpay_order_id, None)

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@app.post("/generate-kundli")
async def generate_kundli(request: KundliRequest) -> StreamingResponse:
    if not settings.allow_free_generation:
        raise HTTPException(status_code=403, detail="Payment required. Use /create-order flow.")

    pdf_bytes, filename = await _build_kundli_pdf(request)
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

from __future__ import annotations

import asyncio

import pytest
import respx
from httpx import Response

from api_client import AstrologyAPIClient
from models import KundliRequest


@pytest.fixture
def sample_request() -> KundliRequest:
    return KundliRequest(
        name="Test User",
        day=15, month=8, year=1990,
        hour=14, min=30,
        lat=23.1765, lon=75.7885,
        tzone=5.5, lang="en",
    )


SAMPLE_PLANETS_JSON = [
    {
        "id": 0, "name": "Sun", "fullDegree": 118.0, "normDegree": 28.0,
        "speed": 0.96, "isRetro": "false", "sign": "Cancer", "signLord": "Moon",
        "nakshatra": "Ashlesha", "nakshatraLord": "Mercury", "nakshatra_pad": 4,
        "house": 9, "is_planet_set": False, "planet_awastha": "Bala",
    },
    {
        "id": 1, "name": "Ascendant", "fullDegree": 236.0, "normDegree": 26.0,
        "speed": 0.0, "isRetro": False, "sign": "Scorpio", "signLord": "Mars",
        "nakshatra": "Jyeshtha", "nakshatraLord": "Mercury", "nakshatra_pad": 3,
        "house": 1, "is_planet_set": False, "planet_awastha": "",
    },
]

SAMPLE_BIRTH_JSON = {
    "year": 1990, "month": 8, "day": 15, "hour": 14, "minute": 30,
    "latitude": 23.1765, "longitude": 75.7885, "timezone": 5.5,
    "sunrise": "06:05:42", "sunset": "19:06:18", "ayanamsha": 23.72,
}


@respx.mock
@pytest.mark.asyncio
async def test_fetch_all_parallel(sample_request: KundliRequest) -> None:
    base = "https://json.astrologyapi.com/v1"
    respx.post(f"{base}/birth_details").mock(return_value=Response(200, json=SAMPLE_BIRTH_JSON))
    respx.post(f"{base}/planets").mock(return_value=Response(200, json=SAMPLE_PLANETS_JSON))
    respx.post(f"{base}/planets/extended").mock(return_value=Response(200, json=SAMPLE_PLANETS_JSON))
    respx.post(f"{base}/houses").mock(return_value=Response(404))
    respx.post(f"{base}/horo_chart/D1").mock(return_value=Response(200, json=[]))
    respx.post(f"{base}/natal_wheel_chart").mock(return_value=Response(200, json={"status": True, "chart_url": "", "msg": "ok"}))
    respx.post(f"{base}/advanced_panchang").mock(return_value=Response(200, json={"day": "Wednesday", "sunrise": "06:00", "sunset": "18:00", "tithi": {}, "nakshatra": {}, "yog": {}, "karan": {}}))
    respx.post(f"{base}/current_vdasha").mock(return_value=Response(200, json={"major": {"planet": "Sun", "start": "1-1-2020", "end": "1-1-2026"}, "minor": {"planet": "Moon", "start": "1-6-2025", "end": "1-12-2025"}, "sub_minor": {"planet": "Mars", "start": "1-9-2025", "end": "1-10-2025"}}))
    respx.post(f"{base}/major_vdasha").mock(return_value=Response(200, json=[{"planet": "Sun", "planet_id": 1, "start": "1-1-2020", "end": "1-1-2026"}]))
    respx.post(f"{base}/kp_birth_chart").mock(return_value=Response(200, json=[]))
    respx.post(f"{base}/sarvashtak").mock(return_value=Response(200, json={"ashtak_varga": {}, "ashtak_points": {"aries": {"sun": 5, "moon": 3, "total": 8}}}))

    async with AstrologyAPIClient() as client:
        data = await client.fetch_all(sample_request)

    assert data.birth_details is not None
    assert data.birth_details.sunrise == "06:05:42"
    assert data.planets is not None
    assert len(data.planets) == 2
    assert data.houses is not None
    assert len(data.houses) == 12
    assert data.panchang is not None
    assert data.major_vdasha is not None
    assert data.sarvashtak is not None
    assert data.sarvashtak[0].sun_points == 5


@respx.mock
@pytest.mark.asyncio
async def test_graceful_failure(sample_request: KundliRequest) -> None:
    base = "https://json.astrologyapi.com/v1"
    respx.post(f"{base}/birth_details").mock(return_value=Response(500))
    respx.post(f"{base}/planets").mock(return_value=Response(500))
    respx.post(f"{base}/planets/extended").mock(return_value=Response(500))
    respx.post(f"{base}/houses").mock(return_value=Response(404))
    respx.post(f"{base}/horo_chart/D1").mock(return_value=Response(500))
    respx.post(f"{base}/natal_wheel_chart").mock(return_value=Response(500))
    respx.post(f"{base}/advanced_panchang").mock(return_value=Response(500))
    respx.post(f"{base}/current_vdasha").mock(return_value=Response(500))
    respx.post(f"{base}/major_vdasha").mock(return_value=Response(500))
    respx.post(f"{base}/kp_birth_chart").mock(return_value=Response(500))
    respx.post(f"{base}/sarvashtak").mock(return_value=Response(500))

    async with AstrologyAPIClient() as client:
        data = await client.fetch_all(sample_request)

    assert data.birth_details is None
    assert data.planets is None
    assert data.panchang is None
    assert data.request.name == "Test User"


@respx.mock
@pytest.mark.asyncio
async def test_bool_retro_accepted(sample_request: KundliRequest) -> None:
    base = "https://json.astrologyapi.com/v1"
    planets_with_bool_retro = [
        {**SAMPLE_PLANETS_JSON[0], "isRetro": True},
    ]
    respx.post(f"{base}/planets").mock(return_value=Response(200, json=planets_with_bool_retro))
    respx.post(f"{base}/birth_details").mock(return_value=Response(404))
    respx.post(f"{base}/planets/extended").mock(return_value=Response(404))
    respx.post(f"{base}/houses").mock(return_value=Response(404))
    respx.post(f"{base}/horo_chart/D1").mock(return_value=Response(404))
    respx.post(f"{base}/natal_wheel_chart").mock(return_value=Response(404))
    respx.post(f"{base}/advanced_panchang").mock(return_value=Response(404))
    respx.post(f"{base}/current_vdasha").mock(return_value=Response(404))
    respx.post(f"{base}/major_vdasha").mock(return_value=Response(404))
    respx.post(f"{base}/kp_birth_chart").mock(return_value=Response(404))
    respx.post(f"{base}/sarvashtak").mock(return_value=Response(404))

    async with AstrologyAPIClient() as client:
        data = await client.fetch_all(sample_request)

    assert data.planets is not None
    assert data.planets[0].isRetro == "true"

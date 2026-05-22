from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from models import (
    AshtakVargaSign,
    AstroDetails,
    AyanamshaEntry,
    BhavMadhya,
    BirthDetails,
    CurrentDasha,
    DashaPeriod,
    GeoName,
    GhatChakra,
    HoroChartSign,
    HouseData,
    KPHouseData,
    KundliData,
    KundliRequest,
    MatchData,
    MatchRequest,
    NatalWheelChart,
    PanchangResponse,
    PlanetAshtakVarga,
    PlanetData,
    PlanetNature,
)

logger = logging.getLogger(__name__)

_api_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _api_semaphore
    if _api_semaphore is None:
        _api_semaphore = asyncio.Semaphore(10)
    return _api_semaphore


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 429:
            return True
        return exc.response.status_code >= 500
    return isinstance(exc, (httpx.ConnectError, httpx.TimeoutException))


PLANET_ID_TO_EN: dict[int, str] = {
    0: "Sun", 1: "Moon", 2: "Mars", 3: "Mercury",
    4: "Jupiter", 5: "Venus", 6: "Saturn",
    7: "Rahu", 8: "Ketu", 9: "Ascendant",
    10: "Uranus", 11: "Neptune", 12: "Pluto",
}


SIGN_ID_TO_EN: dict[int, str] = {
    1: "Aries", 2: "Taurus", 3: "Gemini", 4: "Cancer",
    5: "Leo", 6: "Virgo", 7: "Libra", 8: "Scorpio",
    9: "Sagittarius", 10: "Capricorn", 11: "Aquarius", 12: "Pisces",
}

_SIGN_NAME_NORMALIZE: dict[str, str] = {
    "मेष": "Aries", "वृषभ": "Taurus", "मिथुन": "Gemini",
    "कर्क": "Cancer", "सिंह": "Leo", "कन्या": "Virgo",
    "तुला": "Libra", "वृश्चिक": "Scorpio", "धनु": "Sagittarius",
    "मकर": "Capricorn", "कुंभ": "Aquarius", "मीन": "Pisces",
}


def _normalize_planet_names(planets: list[PlanetData] | None) -> None:
    if not planets:
        return
    for p in planets:
        en_name = PLANET_ID_TO_EN.get(p.id)
        if en_name:
            p.name = en_name
        if p.sign and p.sign not in SIGN_LORDS:
            normalized = _SIGN_NAME_NORMALIZE.get(p.sign)
            if normalized:
                p.sign = normalized
            else:
                sign_idx = int(p.fullDegree / 30) + 1
                p.sign = SIGN_ID_TO_EN.get(sign_idx, p.sign)


SIGN_LORDS: dict[str, str] = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}


class AstrologyAPIClient:
    def __init__(self, lang: str = "en") -> None:
        self._client: httpx.AsyncClient | None = None
        self._lang = lang

    async def __aenter__(self) -> AstrologyAPIClient:
        self._client = httpx.AsyncClient(
            base_url=settings.astro_api_base_url,
            headers={
                "Content-Type": "application/json",
                "x-astrologyapi-key": settings.astro_api_key,
                "Accept-Language": self._lang,
            },
            timeout=httpx.Timeout(settings.astro_api_timeout),
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def _post(self, endpoint: str, payload: dict) -> Any:
        async with _get_semaphore():
            return await self._post_inner(endpoint, payload)

    @retry(
        stop=stop_after_attempt(settings.astro_api_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception(_should_retry),
        reraise=True,
    )
    async def _post_inner(self, endpoint: str, payload: dict) -> Any:
        assert self._client is not None
        start = time.monotonic()
        response = await self._client.post(endpoint, json=payload)
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "API %s → %s (%.0fms)", endpoint, response.status_code, elapsed_ms
        )
        response.raise_for_status()
        return response.json()

    async def _post_form(self, endpoint: str, payload: dict) -> Any:
        assert self._client is not None
        start = time.monotonic()
        response = await self._client.post(
            endpoint, data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "API %s → %s (%.0fms)", endpoint, response.status_code, elapsed_ms
        )
        response.raise_for_status()
        return response.json()

    def _make_payload(self, request: KundliRequest) -> dict:
        return {
            "day": request.day,
            "month": request.month,
            "year": request.year,
            "hour": request.hour,
            "min": request.min,
            "lat": request.lat,
            "lon": request.lon,
            "tzone": request.tzone,
        }

    async def get_birth_details(self, payload: dict) -> BirthDetails | None:
        try:
            raw = await self._post("/birth_details", payload)
            return BirthDetails.model_validate(raw)
        except Exception as e:
            logger.warning("birth_details failed: %s", e)
            return None

    async def get_planets(self, payload: dict) -> list[PlanetData] | None:
        try:
            raw = await self._post("/planets", payload)
            return [PlanetData.model_validate(p) for p in raw]
        except Exception as e:
            logger.warning("planets failed: %s", e)
            return None

    async def get_planets_extended(self, payload: dict) -> list[PlanetData] | None:
        try:
            raw = await self._post("/planets/extended", payload)
            return [PlanetData.model_validate(p) for p in raw]
        except Exception as e:
            logger.warning("planets/extended failed: %s", e)
            return None

    async def get_houses(self, payload: dict) -> list[HouseData] | None:
        try:
            raw = await self._post("/houses", payload)
            if isinstance(raw, list):
                houses = []
                for i, h in enumerate(raw):
                    if isinstance(h, dict):
                        houses.append(HouseData.model_validate(h))
                    else:
                        houses.append(
                            HouseData(house_id=i + 1, sign=str(h), degree=0.0)
                        )
                return houses
            return None
        except Exception as e:
            logger.warning("houses failed: %s", e)
            return None

    async def get_horo_chart_d1(self, payload: dict) -> list[HoroChartSign] | None:
        try:
            raw = await self._post("/horo_chart/D1", payload)
            return [HoroChartSign.model_validate(s) for s in raw]
        except Exception as e:
            logger.warning("horo_chart/D1 failed: %s", e)
            return None

    async def get_natal_wheel_chart(self, payload: dict) -> NatalWheelChart | None:
        try:
            raw = await self._post("/natal_wheel_chart", payload)
            return NatalWheelChart.model_validate(raw)
        except Exception as e:
            logger.warning("natal_wheel_chart failed: %s", e)
            return None

    async def get_panchang(self, payload: dict) -> PanchangResponse | None:
        try:
            raw = await self._post("/advanced_panchang", payload)
            return PanchangResponse.model_validate(raw)
        except Exception as e:
            logger.warning("advanced_panchang failed: %s", e)
            return None

    async def get_basic_panchang(self, payload: dict) -> dict | None:
        try:
            return await self._post("/basic_panchang", payload)
        except Exception as e:
            logger.warning("basic_panchang failed: %s", e)
            return None

    async def get_basic_panchang_sunrise(self, payload: dict) -> dict | None:
        try:
            return await self._post("/basic_panchang/sunrise", payload)
        except Exception as e:
            logger.warning("basic_panchang/sunrise failed: %s", e)
            return None

    async def get_advanced_panchang_sunrise(self, payload: dict) -> dict | None:
        try:
            return await self._post("/advanced_panchang/sunrise", payload)
        except Exception as e:
            logger.warning("advanced_panchang/sunrise failed: %s", e)
            return None

    async def get_planet_panchang(self, payload: dict) -> dict | None:
        try:
            return await self._post("/planet_panchang", payload)
        except Exception as e:
            logger.warning("planet_panchang failed: %s", e)
            return None

    async def get_planet_panchang_sunrise(self, payload: dict) -> dict | None:
        try:
            return await self._post("/planet_panchang/sunrise", payload)
        except Exception as e:
            logger.warning("planet_panchang/sunrise failed: %s", e)
            return None

    async def get_chaughadiya_muhurta(self, payload: dict) -> dict | None:
        try:
            return await self._post("/chaughadiya_muhurta", payload)
        except Exception as e:
            logger.warning("chaughadiya_muhurta failed: %s", e)
            return None

    async def get_hora_muhurta(self, payload: dict) -> dict | None:
        try:
            return await self._post("/hora_muhurta", payload)
        except Exception as e:
            logger.warning("hora_muhurta failed: %s", e)
            return None

    async def get_hora_muhurta_dinman(self, payload: dict) -> dict | None:
        try:
            return await self._post("/hora_muhurta_dinman", payload)
        except Exception as e:
            logger.warning("hora_muhurta_dinman failed: %s", e)
            return None

    async def get_panchang_chart(self, payload: dict) -> dict | None:
        try:
            return await self._post("/panchang_chart/sunrise", payload)
        except Exception as e:
            logger.warning("panchang_chart/sunrise failed: %s", e)
            return None

    async def get_tamil_month_panchang(self, payload: dict) -> dict | None:
        try:
            return await self._post("/tamil_month_panchang", payload)
        except Exception as e:
            logger.warning("tamil_month_panchang failed: %s", e)
            return None

    async def get_tamil_panchang(self, payload: dict) -> dict | None:
        try:
            return await self._post("/tamil_panchang", payload)
        except Exception as e:
            logger.warning("tamil_panchang failed: %s", e)
            return None

    async def get_panchang_festival(self, payload: dict) -> dict | None:
        try:
            return await self._post("/panchang_festival", payload)
        except Exception as e:
            logger.warning("panchang_festival failed: %s", e)
            return None

    async def get_current_vdasha(self, payload: dict) -> CurrentDasha | None:
        try:
            raw = await self._post("/current_vdasha", payload)
            return CurrentDasha.model_validate(raw)
        except Exception as e:
            logger.warning("current_vdasha failed: %s", e)
            return None

    async def get_major_vdasha(self, payload: dict) -> list[DashaPeriod] | None:
        try:
            raw = await self._post("/major_vdasha", payload)
            return [DashaPeriod.model_validate(d) for d in raw]
        except Exception as e:
            logger.warning("major_vdasha failed: %s", e)
            return None

    async def get_kp_birth_chart(self, payload: dict) -> list[KPHouseData] | None:
        try:
            raw = await self._post("/kp_birth_chart", payload)
            return [KPHouseData.model_validate(h) for h in raw]
        except Exception as e:
            logger.warning("kp_birth_chart failed: %s", e)
            return None

    async def get_sarvashtak(self, payload: dict) -> list[AshtakVargaSign] | None:
        try:
            raw = await self._post("/sarvashtak", payload)
            return self._parse_sarvashtak(raw)
        except Exception as e:
            logger.warning("sarvashtak failed: %s", e)
            return None

    @staticmethod
    def _parse_sarvashtak(raw: dict) -> list[AshtakVargaSign]:
        ashtak_points = raw.get("ashtak_points", {})
        sign_names = [
            "aries", "taurus", "gemini", "cancer", "leo", "virgo",
            "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
        ]
        sign_labels = [
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
        ]
        results: list[AshtakVargaSign] = []
        for i, key in enumerate(sign_names):
            pts = ashtak_points.get(key, {})
            results.append(
                AshtakVargaSign(
                    sign=sign_labels[i],
                    sign_id=i + 1,
                    sun_points=pts.get("sun", 0),
                    moon_points=pts.get("moon", 0),
                    mars_points=pts.get("mars", 0),
                    mercury_points=pts.get("mercury", 0),
                    jupiter_points=pts.get("jupiter", 0),
                    venus_points=pts.get("venus", 0),
                    saturn_points=pts.get("saturn", 0),
                    ascendant_points=pts.get("ascendant", 0),
                    total_points=pts.get("total", 0),
                )
            )
        return results

    async def get_geo_details(self, place: str, max_rows: int = 6) -> list[GeoName] | None:
        try:
            raw = await self._post_form("/geo_details", {"place": place, "maxRows": max_rows})
            geonames = raw.get("geonames", [])
            return [GeoName.model_validate(g) for g in geonames]
        except Exception as e:
            logger.warning("geo_details failed: %s", e)
            return None

    async def get_timezone_with_dst(self, payload: dict) -> dict | None:
        try:
            raw = await self._post("/timezone_with_dst", payload)
            return raw
        except Exception as e:
            logger.warning("timezone_with_dst failed: %s", e)
            return None

    async def get_ayanamsha(self, payload: dict) -> list[AyanamshaEntry] | None:
        try:
            raw = await self._post("/ayanamsha", payload)
            return [AyanamshaEntry.model_validate(a) for a in raw]
        except Exception as e:
            logger.warning("ayanamsha failed: %s", e)
            return None

    async def get_astro_details(self, payload: dict) -> AstroDetails | None:
        try:
            raw = await self._post("/astro_details", payload)
            return AstroDetails.model_validate(raw)
        except Exception as e:
            logger.warning("astro_details failed: %s", e)
            return None

    async def get_ghat_chakra(self, payload: dict) -> GhatChakra | None:
        try:
            raw = await self._post("/ghat_chakra", payload)
            return GhatChakra.model_validate(raw)
        except Exception as e:
            logger.warning("ghat_chakra failed: %s", e)
            return None

    async def get_bhav_madhya(self, payload: dict) -> BhavMadhya | None:
        try:
            raw = await self._post("/bhav_madhya", payload)
            return BhavMadhya.model_validate(raw)
        except Exception as e:
            logger.warning("bhav_madhya failed: %s", e)
            return None

    async def get_planet_nature(self, payload: dict) -> PlanetNature | None:
        try:
            raw = await self._post("/planet_nature", payload)
            return PlanetNature.model_validate(raw)
        except Exception as e:
            logger.warning("planet_nature failed: %s", e)
            return None

    async def get_panchada_maitri(self, payload: dict) -> dict | None:
        try:
            raw = await self._post("/panchada_maitri", payload)
            return raw
        except Exception as e:
            logger.warning("panchada_maitri failed: %s", e)
            return None

    async def get_planet_ashtak(self, payload: dict, planet_name: str) -> PlanetAshtakVarga | None:
        try:
            raw = await self._post(f"/planet_ashtak/{planet_name}", payload)
            return PlanetAshtakVarga.model_validate(raw)
        except Exception as e:
            logger.warning("planet_ashtak/%s failed: %s", planet_name, e)
            return None

    async def get_horo_chart(self, payload: dict, chart_id: str) -> list[HoroChartSign] | None:
        try:
            raw = await self._post(f"/horo_chart/{chart_id}", payload)
            return [HoroChartSign.model_validate(s) for s in raw]
        except Exception as e:
            logger.warning("horo_chart/%s failed: %s", chart_id, e)
            return None

    async def get_horo_chart_image(self, payload: dict, chart_id: str) -> dict | None:
        try:
            raw = await self._post(f"/horo_chart_image/{chart_id}", payload)
            return raw
        except Exception as e:
            logger.warning("horo_chart_image/%s failed: %s", chart_id, e)
            return None

    async def get_horo_chart_extended(self, payload: dict) -> dict | None:
        try:
            raw = await self._post("/horo_chart_extended", payload)
            return raw
        except Exception as e:
            logger.warning("horo_chart_extended failed: %s", e)
            return None

    async def get_general_ascendant_report(self, payload: dict) -> dict | None:
        try:
            return await self._post("/general_ascendant_report", payload)
        except Exception as e:
            logger.warning("general_ascendant_report failed: %s", e)
            return None

    async def get_general_nakshatra_report(self, payload: dict) -> dict | None:
        try:
            return await self._post("/general_nakshatra_report", payload)
        except Exception as e:
            logger.warning("general_nakshatra_report failed: %s", e)
            return None

    async def get_general_house_report(self, payload: dict, planet_name: str) -> dict | None:
        try:
            return await self._post(f"/general_house_report/{planet_name}", payload)
        except Exception as e:
            logger.warning("general_house_report/%s failed: %s", planet_name, e)
            return None

    async def get_general_rashi_report(self, payload: dict, planet_name: str) -> dict | None:
        try:
            return await self._post(f"/general_rashi_report/{planet_name}", payload)
        except Exception as e:
            logger.warning("general_rashi_report/%s failed: %s", planet_name, e)
            return None

    async def get_simple_manglik(self, payload: dict) -> dict | None:
        try:
            return await self._post("/simple_manglik", payload)
        except Exception as e:
            logger.warning("simple_manglik failed: %s", e)
            return None

    async def get_manglik(self, payload: dict) -> dict | None:
        try:
            return await self._post("/manglik", payload)
        except Exception as e:
            logger.warning("manglik failed: %s", e)
            return None

    async def get_kalsarpa_details(self, payload: dict) -> dict | None:
        try:
            return await self._post("/kalsarpa_details", payload)
        except Exception as e:
            logger.warning("kalsarpa_details failed: %s", e)
            return None

    async def get_sadhesati_current_status(self, payload: dict) -> dict | None:
        try:
            return await self._post("/sadhesati_current_status", payload)
        except Exception as e:
            logger.warning("sadhesati_current_status failed: %s", e)
            return None

    async def get_sadhesati_life_details(self, payload: dict) -> dict | None:
        try:
            return await self._post("/sadhesati_life_details", payload)
        except Exception as e:
            logger.warning("sadhesati_life_details failed: %s", e)
            return None

    async def get_pitra_dosha_report(self, payload: dict) -> dict | None:
        try:
            return await self._post("/pitra_dosha_report", payload)
        except Exception as e:
            logger.warning("pitra_dosha_report failed: %s", e)
            return None

    async def get_puja_suggestion(self, payload: dict) -> dict | None:
        try:
            return await self._post("/puja_suggestion", payload)
        except Exception as e:
            logger.warning("puja_suggestion failed: %s", e)
            return None

    async def get_basic_gem_suggestion(self, payload: dict) -> dict | None:
        try:
            return await self._post("/basic_gem_suggestion", payload)
        except Exception as e:
            logger.warning("basic_gem_suggestion failed: %s", e)
            return None

    async def get_rudraksha_suggestion(self, payload: dict) -> dict | None:
        try:
            return await self._post("/rudraksha_suggestion", payload)
        except Exception as e:
            logger.warning("rudraksha_suggestion failed: %s", e)
            return None

    async def get_sadhesati_remedies(self, payload: dict) -> dict | None:
        try:
            return await self._post("/sadhesati_remedies", payload)
        except Exception as e:
            logger.warning("sadhesati_remedies failed: %s", e)
            return None

    async def get_daily_nakshatra_prediction(self, payload: dict) -> dict | None:
        try:
            return await self._post("/daily_nakshatra_prediction", payload)
        except Exception as e:
            logger.warning("daily_nakshatra_prediction failed: %s", e)
            return None

    async def get_daily_nakshatra_prediction_next(self, payload: dict) -> dict | None:
        try:
            return await self._post("/daily_nakshatra_prediction/next", payload)
        except Exception as e:
            logger.warning("daily_nakshatra_prediction/next failed: %s", e)
            return None

    async def get_daily_nakshatra_prediction_previous(self, payload: dict) -> dict | None:
        try:
            return await self._post("/daily_nakshatra_prediction/previous", payload)
        except Exception as e:
            logger.warning("daily_nakshatra_prediction/previous failed: %s", e)
            return None

    async def get_varshaphal_year_chart(self, payload: dict) -> dict | None:
        try:
            return await self._post("/varshaphal_year_chart", payload)
        except Exception as e:
            logger.warning("varshaphal_year_chart failed: %s", e)
            return None

    async def get_varshaphal_month_chart(self, payload: dict) -> dict | None:
        try:
            return await self._post("/varshaphal_month_chart", payload)
        except Exception as e:
            logger.warning("varshaphal_month_chart failed: %s", e)
            return None

    async def get_varshaphal_details(self, payload: dict) -> dict | None:
        try:
            return await self._post("/varshaphal_details", payload)
        except Exception as e:
            logger.warning("varshaphal_details failed: %s", e)
            return None

    async def get_varshaphal_planets(self, payload: dict) -> dict | None:
        try:
            return await self._post("/varshaphal_planets", payload)
        except Exception as e:
            logger.warning("varshaphal_planets failed: %s", e)
            return None

    async def get_varshaphal_muntha(self, payload: dict) -> dict | None:
        try:
            return await self._post("/varshaphal_muntha", payload)
        except Exception as e:
            logger.warning("varshaphal_muntha failed: %s", e)
            return None

    async def get_varshaphal_mudda_dasha(self, payload: dict) -> dict | None:
        try:
            return await self._post("/varshaphal_mudda_dasha", payload)
        except Exception as e:
            logger.warning("varshaphal_mudda_dasha failed: %s", e)
            return None

    async def get_varshaphal_panchavargeeya_bala(self, payload: dict) -> dict | None:
        try:
            return await self._post("/varshaphal_panchavargeeya_bala", payload)
        except Exception as e:
            logger.warning("varshaphal_panchavargeeya_bala failed: %s", e)
            return None

    async def get_varshaphal_harsha_bala(self, payload: dict) -> dict | None:
        try:
            return await self._post("/varshaphal_harsha_bala", payload)
        except Exception as e:
            logger.warning("varshaphal_harsha_bala failed: %s", e)
            return None

    async def get_varshaphal_saham_points(self, payload: dict) -> dict | None:
        try:
            return await self._post("/varshaphal_saham_points", payload)
        except Exception as e:
            logger.warning("varshaphal_saham_points failed: %s", e)
            return None

    async def get_varshaphal_yoga(self, payload: dict) -> dict | None:
        try:
            return await self._post("/varshaphal_yoga", payload)
        except Exception as e:
            logger.warning("varshaphal_yoga failed: %s", e)
            return None

    async def get_current_vdasha_all(self, payload: dict) -> dict | None:
        try:
            return await self._post("/current_vdasha_all", payload)
        except Exception as e:
            logger.warning("current_vdasha_all failed: %s", e)
            return None

    async def get_sub_vdasha(self, payload: dict, md: str) -> list | None:
        try:
            return await self._post(f"/sub_vdasha/{md}", payload)
        except Exception as e:
            logger.warning("sub_vdasha/%s failed: %s", md, e)
            return None

    async def get_sub_sub_vdasha(self, payload: dict, md: str, ad: str) -> list | None:
        try:
            return await self._post(f"/sub_sub_vdasha/{md}/{ad}", payload)
        except Exception as e:
            logger.warning("sub_sub_vdasha/%s/%s failed: %s", md, ad, e)
            return None

    async def get_sub_sub_sub_vdasha(self, payload: dict, md: str, ad: str, pd: str) -> list | None:
        try:
            return await self._post(f"/sub_sub_sub_vdasha/{md}/{ad}/{pd}", payload)
        except Exception as e:
            logger.warning("sub_sub_sub_vdasha failed: %s", e)
            return None

    async def get_sub_sub_sub_sub_vdasha(self, payload: dict, md: str, ad: str, pd: str, sd: str) -> list | None:
        try:
            return await self._post(f"/sub_sub_sub_sub_vdasha/{md}/{ad}/{pd}/{sd}", payload)
        except Exception as e:
            logger.warning("sub_sub_sub_sub_vdasha failed: %s", e)
            return None

    async def get_kp_planets(self, payload: dict) -> list | None:
        try:
            return await self._post("/kp_planets", payload)
        except Exception as e:
            logger.warning("kp_planets failed: %s", e)
            return None

    async def get_kp_house_cusps(self, payload: dict) -> list | None:
        try:
            return await self._post("/kp_house_cusps", payload)
        except Exception as e:
            logger.warning("kp_house_cusps failed: %s", e)
            return None

    async def get_kp_house_significator(self, payload: dict) -> dict | None:
        try:
            return await self._post("/kp_house_significator", payload)
        except Exception as e:
            logger.warning("kp_house_significator failed: %s", e)
            return None

    async def get_kp_planet_significator(self, payload: dict) -> dict | None:
        try:
            return await self._post("/kp_planet_significator", payload)
        except Exception as e:
            logger.warning("kp_planet_significator failed: %s", e)
            return None

    async def get_major_yogini_dasha(self, payload: dict) -> list | None:
        try:
            return await self._post("/major_yogini_dasha", payload)
        except Exception as e:
            logger.warning("major_yogini_dasha failed: %s", e)
            return None

    async def get_current_yogini_dasha(self, payload: dict) -> dict | None:
        try:
            return await self._post("/current_yogini_dasha", payload)
        except Exception as e:
            logger.warning("current_yogini_dasha failed: %s", e)
            return None

    async def get_sub_yogini_dasha(self, payload: dict) -> list | None:
        try:
            return await self._post("/sub_yogini_dasha", payload)
        except Exception as e:
            logger.warning("sub_yogini_dasha failed: %s", e)
            return None

    # --- Char (Jaimini) Dasha ---
    async def get_current_chardasha(self, payload: dict) -> dict | None:
        try:
            return await self._post("/current_chardasha", payload)
        except Exception as e:
            logger.warning("current_chardasha failed: %s", e)
            return None

    async def get_major_chardasha(self, payload: dict) -> list | None:
        try:
            return await self._post("/major_chardasha", payload)
        except Exception as e:
            logger.warning("major_chardasha failed: %s", e)
            return None

    async def get_sub_chardasha(self, payload: dict, md: str) -> list | None:
        try:
            return await self._post(f"/sub_chardasha/{md}", payload)
        except Exception as e:
            logger.warning("sub_chardasha/%s failed: %s", md, e)
            return None

    # --- Numerology ---
    async def get_numero_table(self, payload: dict) -> dict | None:
        try:
            return await self._post("/numero_table", payload)
        except Exception as e:
            logger.warning("numero_table failed: %s", e)
            return None

    async def get_numero_report(self, payload: dict) -> dict | None:
        try:
            return await self._post("/numero_report", payload)
        except Exception as e:
            logger.warning("numero_report failed: %s", e)
            return None

    async def get_numero_fav_time(self, payload: dict) -> dict | None:
        try:
            return await self._post("/numero_fav_time", payload)
        except Exception as e:
            logger.warning("numero_fav_time failed: %s", e)
            return None

    async def get_numero_place_vastu(self, payload: dict) -> dict | None:
        try:
            return await self._post("/numero_place_vastu", payload)
        except Exception as e:
            logger.warning("numero_place_vastu failed: %s", e)
            return None

    async def get_numero_fasts_report(self, payload: dict) -> dict | None:
        try:
            return await self._post("/numero_fasts_report", payload)
        except Exception as e:
            logger.warning("numero_fasts_report failed: %s", e)
            return None

    async def get_numero_fav_lord(self, payload: dict) -> dict | None:
        try:
            return await self._post("/numero_fav_lord", payload)
        except Exception as e:
            logger.warning("numero_fav_lord failed: %s", e)
            return None

    async def get_numero_fav_mantra(self, payload: dict) -> dict | None:
        try:
            return await self._post("/numero_fav_mantra", payload)
        except Exception as e:
            logger.warning("numero_fav_mantra failed: %s", e)
            return None

    async def get_numero_prediction_daily(self, payload: dict) -> dict | None:
        try:
            return await self._post("/numero_prediction/daily", payload)
        except Exception as e:
            logger.warning("numero_prediction/daily failed: %s", e)
            return None

    # --- Lal Kitab ---
    async def get_lalkitab_horoscope(self, payload: dict) -> dict | None:
        try:
            return await self._post("/lalkitab_horoscope", payload)
        except Exception as e:
            logger.warning("lalkitab_horoscope failed: %s", e)
            return None

    async def get_lalkitab_planets(self, payload: dict) -> dict | None:
        try:
            return await self._post("/lalkitab_planets", payload)
        except Exception as e:
            logger.warning("lalkitab_planets failed: %s", e)
            return None

    async def get_lalkitab_houses(self, payload: dict) -> dict | None:
        try:
            return await self._post("/lalkitab_houses", payload)
        except Exception as e:
            logger.warning("lalkitab_houses failed: %s", e)
            return None

    async def get_lalkitab_debts(self, payload: dict) -> dict | None:
        try:
            return await self._post("/lalkitab_debts", payload)
        except Exception as e:
            logger.warning("lalkitab_debts failed: %s", e)
            return None

    async def get_lalkitab_remedies(self, payload: dict, planet_name: str) -> dict | None:
        try:
            return await self._post(f"/lalkitab_remedies/{planet_name}", payload)
        except Exception as e:
            logger.warning("lalkitab_remedies/%s failed: %s", planet_name, e)
            return None

    # --- KP Extended ---
    async def get_kp_horoscope(self, payload: dict) -> dict | None:
        try:
            p = {**payload, "aspects": "true"}
            return await self._post("/kp_horoscope", p)
        except Exception as e:
            logger.warning("kp_horoscope failed: %s", e)
            return None

    # --- Biorhythm ---
    async def get_biorhythm(self, payload: dict) -> dict | None:
        try:
            return await self._post("/biorhythm", payload)
        except Exception as e:
            logger.warning("biorhythm failed: %s", e)
            return None

    async def get_moon_biorhythm(self, payload: dict) -> dict | None:
        try:
            return await self._post("/moon_biorhythm", payload)
        except Exception as e:
            logger.warning("moon_biorhythm failed: %s", e)
            return None

    # --- Monthly Panchang ---
    async def get_monthly_panchang(self, payload: dict) -> dict | None:
        try:
            return await self._post("/monthly_panchang", payload)
        except Exception as e:
            logger.warning("monthly_panchang failed: %s", e)
            return None

    def _make_numero_payload(self, request: KundliRequest) -> dict:
        return {
            "day": request.day,
            "month": request.month,
            "year": request.year,
            "name": request.name,
        }

    async def _download_chart_svg(self, url: str) -> str | None:
        if not url or not self._client:
            return None
        try:
            resp = await self._client.get(url, timeout=15)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.warning("chart SVG download failed: %s", e)
            return None

    async def _noop(self) -> None:
        return None

    def _make_match_payload(self, request: MatchRequest) -> dict:
        return {
            "m_day": request.m_day, "m_month": request.m_month, "m_year": request.m_year,
            "m_hour": request.m_hour, "m_min": request.m_min,
            "m_lat": request.m_lat, "m_lon": request.m_lon, "m_tzone": request.m_tzone,
            "f_day": request.f_day, "f_month": request.f_month, "f_year": request.f_year,
            "f_hour": request.f_hour, "f_min": request.f_min,
            "f_lat": request.f_lat, "f_lon": request.f_lon, "f_tzone": request.f_tzone,
        }

    async def get_match_birth_details(self, payload: dict) -> dict | None:
        try:
            return await self._post("/match_birth_details", payload)
        except Exception as e:
            logger.warning("match_birth_details failed: %s", e)
            return None

    async def get_match_astro_details(self, payload: dict) -> dict | None:
        try:
            return await self._post("/match_astro_details", payload)
        except Exception as e:
            logger.warning("match_astro_details failed: %s", e)
            return None

    async def get_match_planet_details(self, payload: dict) -> dict | None:
        try:
            return await self._post("/match_planet_details", payload)
        except Exception as e:
            logger.warning("match_planet_details failed: %s", e)
            return None

    async def get_match_obstructions(self, payload: dict) -> dict | None:
        try:
            return await self._post("/match_obstructions", payload)
        except Exception as e:
            logger.warning("match_obstructions failed: %s", e)
            return None

    async def get_match_manglik_report(self, payload: dict) -> dict | None:
        try:
            return await self._post("/match_manglik_report", payload)
        except Exception as e:
            logger.warning("match_manglik_report failed: %s", e)
            return None

    async def get_match_ashtakoot_points(self, payload: dict) -> dict | None:
        try:
            return await self._post("/match_ashtakoot_points", payload)
        except Exception as e:
            logger.warning("match_ashtakoot_points failed: %s", e)
            return None

    async def get_match_dashakoot_points(self, payload: dict) -> dict | None:
        try:
            return await self._post("/match_dashakoot_points", payload)
        except Exception as e:
            logger.warning("match_dashakoot_points failed: %s", e)
            return None

    async def get_match_percentage(self, payload: dict) -> dict | None:
        try:
            return await self._post("/match_percentage", payload)
        except Exception as e:
            logger.warning("match_percentage failed: %s", e)
            return None

    async def get_match_making_report(self, payload: dict) -> dict | None:
        try:
            return await self._post("/match_making_report", payload)
        except Exception as e:
            logger.warning("match_making_report failed: %s", e)
            return None

    async def get_match_making_detailed_report(self, payload: dict) -> dict | None:
        try:
            return await self._post("/match_making_detailed_report", payload)
        except Exception as e:
            logger.warning("match_making_detailed_report failed: %s", e)
            return None

    async def fetch_match(self, request: MatchRequest) -> MatchData:
        payload = self._make_match_payload(request)

        results = await asyncio.gather(
            self.get_match_birth_details(payload),
            self.get_match_astro_details(payload),
            self.get_match_planet_details(payload),
            self.get_match_obstructions(payload),
            self.get_match_manglik_report(payload),
            self.get_match_ashtakoot_points(payload),
            self.get_match_dashakoot_points(payload),
            self.get_match_percentage(payload),
            self.get_match_making_report(payload),
            self.get_match_making_detailed_report(payload),
            return_exceptions=True,
        )

        def safe(val: Any) -> Any:
            return None if isinstance(val, BaseException) else val

        return MatchData(
            request=request,
            match_birth_details=safe(results[0]),
            match_astro_details=safe(results[1]),
            match_planet_details=safe(results[2]),
            match_obstructions=safe(results[3]),
            match_manglik_report=safe(results[4]),
            match_ashtakoot_points=safe(results[5]),
            match_dashakoot_points=safe(results[6]),
            match_percentage=safe(results[7]),
            match_report=safe(results[8]),
            match_detailed_report=safe(results[9]),
        )

    async def fetch_all(self, request: KundliRequest) -> KundliData:
        payload = self._make_payload(request)
        payload_with_ayan = {**payload, "ayanamsha": "LAHIRI"}
        numero_payload = self._make_numero_payload(request)

        # Phase 1: all independent parallel calls
        results = await asyncio.gather(
            self.get_birth_details(payload),              # 0
            self.get_planets(payload),                     # 1
            self.get_planets_extended(payload),             # 2
            self.get_houses(payload),                       # 3
            self.get_horo_chart_d1(payload),                # 4
            self.get_natal_wheel_chart(payload),            # 5
            self.get_panchang(payload_with_ayan),              # 6
            self.get_current_vdasha(payload),               # 7
            self.get_major_vdasha(payload),                 # 8
            self.get_kp_birth_chart(payload),               # 9
            self.get_sarvashtak(payload),                   # 10
            self.get_ayanamsha(payload),                    # 11
            self.get_astro_details(payload_with_ayan),      # 12
            self.get_ghat_chakra(payload_with_ayan),        # 13
            self.get_bhav_madhya(payload_with_ayan),        # 14
            self.get_planet_nature(payload_with_ayan),      # 15
            self.get_panchada_maitri(payload_with_ayan),    # 16
            self.get_horo_chart_extended(payload_with_ayan),  # 17
            self.get_general_ascendant_report(payload_with_ayan),   # 18
            self.get_general_nakshatra_report(payload_with_ayan),   # 19
            self.get_simple_manglik(payload_with_ayan),     # 20
            self.get_manglik(payload_with_ayan),            # 21
            self.get_kalsarpa_details(payload_with_ayan),   # 22
            self.get_sadhesati_current_status(payload_with_ayan),  # 23
            self.get_sadhesati_life_details(payload_with_ayan),    # 24
            self.get_pitra_dosha_report(payload_with_ayan),        # 25
            self.get_puja_suggestion(payload_with_ayan),    # 26
            self.get_basic_gem_suggestion(payload_with_ayan),  # 27
            self.get_rudraksha_suggestion(payload_with_ayan),  # 28
            self.get_sadhesati_remedies(payload),           # 29
            self.get_daily_nakshatra_prediction(payload),   # 30
            self.get_daily_nakshatra_prediction_next(payload),     # 31
            self.get_daily_nakshatra_prediction_previous(payload), # 32
            self.get_varshaphal_year_chart(payload_with_ayan),     # 33
            self.get_varshaphal_month_chart(payload_with_ayan),    # 34
            self.get_varshaphal_details(payload_with_ayan),        # 35
            self.get_varshaphal_planets(payload_with_ayan),        # 36
            self.get_varshaphal_muntha(payload_with_ayan),         # 37
            self.get_varshaphal_mudda_dasha(payload_with_ayan),    # 38
            self.get_varshaphal_panchavargeeya_bala(payload_with_ayan),  # 39
            self.get_varshaphal_harsha_bala(payload_with_ayan),    # 40
            self.get_varshaphal_saham_points(payload_with_ayan),   # 41
            self.get_varshaphal_yoga(payload_with_ayan),           # 42
            self.get_current_vdasha_all(payload_with_ayan),        # 43
            self.get_kp_planets(payload_with_ayan),         # 44
            self.get_kp_house_cusps(payload_with_ayan),     # 45
            self.get_kp_house_significator(payload_with_ayan),     # 46
            self.get_kp_planet_significator(payload_with_ayan),    # 47
            self.get_major_yogini_dasha(payload_with_ayan),        # 48
            self.get_current_yogini_dasha(payload_with_ayan),      # 49
            self.get_sub_yogini_dasha(payload_with_ayan),          # 50
            self.get_basic_panchang(payload),                       # 51
            self.get_basic_panchang_sunrise(payload),               # 52
            self.get_advanced_panchang_sunrise(payload),            # 53
            self.get_planet_panchang(payload),                      # 54
            self.get_planet_panchang_sunrise(payload),              # 55
            self.get_chaughadiya_muhurta(payload),                  # 56
            self.get_hora_muhurta(payload),                         # 57
            self.get_hora_muhurta_dinman(payload),                  # 58
            self.get_panchang_chart(payload),                       # 59
            self.get_tamil_month_panchang(payload),                 # 60
            self.get_tamil_panchang(payload),                       # 61
            self.get_panchang_festival(payload),                    # 62
            # --- New: Char Dasha ---
            self.get_current_chardasha(payload_with_ayan),         # 63
            self.get_major_chardasha(payload_with_ayan),           # 64
            # --- New: Numerology ---
            self.get_numero_table(numero_payload),                 # 65
            self.get_numero_report(numero_payload),                # 66
            self.get_numero_fav_time(numero_payload),              # 67
            self.get_numero_place_vastu(numero_payload),           # 68
            self.get_numero_fasts_report(numero_payload),          # 69
            self.get_numero_fav_lord(numero_payload),              # 70
            self.get_numero_fav_mantra(numero_payload),            # 71
            self.get_numero_prediction_daily(numero_payload),      # 72
            # --- New: Lal Kitab ---
            self.get_lalkitab_horoscope(payload_with_ayan),        # 73
            self.get_lalkitab_planets(payload_with_ayan),          # 74
            self.get_lalkitab_houses(payload_with_ayan),           # 75
            self.get_lalkitab_debts(payload_with_ayan),            # 76
            # --- New: KP Extended ---
            self.get_kp_horoscope(payload_with_ayan),              # 77
            # --- New: Biorhythm ---
            self.get_biorhythm(payload_with_ayan),                 # 78
            self.get_moon_biorhythm(payload_with_ayan),            # 79
            # --- New: Monthly Panchang ---
            self.get_monthly_panchang(payload),                    # 80
            return_exceptions=True,
        )

        def safe(val: Any) -> Any:
            return None if isinstance(val, BaseException) else val

        # Phase 2: per-planet and per-chart parallel calls
        planet_names = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        report_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        chart_ids = [
            "D2", "D3", "D4", "D5", "D7", "D8", "D9", "D10",
            "D12", "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60",
        ]

        phase2a = await asyncio.gather(
            *[self.get_planet_ashtak(payload_with_ayan, p) for p in planet_names],
            *[self.get_horo_chart(payload_with_ayan, c) for c in chart_ids],
            return_exceptions=True,
        )

        planet_ashtak: dict = {}
        for i, pname in enumerate(planet_names):
            val = safe(phase2a[i])
            if val is not None:
                planet_ashtak[pname] = val

        horo_charts: dict = {}
        for i, cid in enumerate(chart_ids):
            val = safe(phase2a[len(planet_names) + i])
            if val is not None:
                horo_charts[cid] = val

        phase2b = await asyncio.gather(
            *[self.get_horo_chart_image(payload_with_ayan, c) for c in chart_ids],
            *[self.get_general_house_report(payload_with_ayan, p) for p in report_planets],
            return_exceptions=True,
        )

        horo_chart_images: dict = {}
        for i, cid in enumerate(chart_ids):
            val = safe(phase2b[i])
            if val is not None and isinstance(val, dict):
                img_url = val.get("chart_url", "")
                raw_svg = val.get("svg", "")
                if img_url:
                    horo_chart_images[cid] = img_url
                elif raw_svg and raw_svg.strip().startswith("<"):
                    b64 = base64.b64encode(raw_svg.encode("utf-8")).decode("ascii")
                    horo_chart_images[cid] = f"data:image/svg+xml;base64,{b64}"

        general_house_reports: dict = {}
        for i, pname in enumerate(report_planets):
            val = safe(phase2b[len(chart_ids) + i])
            if val is not None:
                general_house_reports[pname] = val

        phase2c = await asyncio.gather(
            *[self.get_general_rashi_report(payload_with_ayan, p) for p in report_planets],
            *[self.get_lalkitab_remedies(payload_with_ayan, p) for p in report_planets],
            return_exceptions=True,
        )

        general_rashi_reports: dict = {}
        for i, pname in enumerate(report_planets):
            val = safe(phase2c[i])
            if val is not None:
                general_rashi_reports[pname] = val

        lalkitab_remedies: dict = {}
        for i, pname in enumerate(report_planets):
            val = safe(phase2c[len(report_planets) + i])
            if val is not None:
                lalkitab_remedies[pname] = val

        # Phase 3: sub-dasha calls (need current_vdasha planet names)
        current_vdasha = safe(results[7])
        sub_vdasha_data = None
        sub_sub_vdasha_data = None
        sub_sub_sub_vdasha_data = None
        sub_sub_sub_sub_vdasha_data = None

        if current_vdasha and current_vdasha.major.planet:
            md = PLANET_ID_TO_EN.get(current_vdasha.major.planet_id, current_vdasha.major.planet)
            ad = PLANET_ID_TO_EN.get(current_vdasha.minor.planet_id, current_vdasha.minor.planet)
            pd_name = PLANET_ID_TO_EN.get(current_vdasha.sub_minor.planet_id, current_vdasha.sub_minor.planet)
            sd = PLANET_ID_TO_EN.get(current_vdasha.sub_sub_minor.planet_id, current_vdasha.sub_sub_minor.planet)

            sub_dasha_coros = [self.get_sub_vdasha(payload_with_ayan, md)]
            if ad:
                sub_dasha_coros.append(self.get_sub_sub_vdasha(payload_with_ayan, md, ad))
            else:
                sub_dasha_coros.append(self._noop())
            if ad and pd_name:
                sub_dasha_coros.append(self.get_sub_sub_sub_vdasha(payload_with_ayan, md, ad, pd_name))
            else:
                sub_dasha_coros.append(self._noop())
            if ad and pd_name and sd:
                sub_dasha_coros.append(self.get_sub_sub_sub_sub_vdasha(payload_with_ayan, md, ad, pd_name, sd))
            else:
                sub_dasha_coros.append(self._noop())

            sub_results = await asyncio.gather(*sub_dasha_coros, return_exceptions=True)
            sub_vdasha_data = safe(sub_results[0])
            sub_sub_vdasha_data = safe(sub_results[1])
            sub_sub_sub_vdasha_data = safe(sub_results[2])
            sub_sub_sub_sub_vdasha_data = safe(sub_results[3])

        # Phase 3b: Char Dasha sub-periods (need current_chardasha sign)
        current_chardasha_data = safe(results[63])
        sub_chardasha_data = None
        if current_chardasha_data and isinstance(current_chardasha_data, dict):
            cd_sign = current_chardasha_data.get("sign_id") or current_chardasha_data.get("sign", "")
            if cd_sign:
                sub_chardasha_data = await self.get_sub_chardasha(payload_with_ayan, str(cd_sign))

        natal_wheel = safe(results[5])
        chart_svg: str | None = None
        if natal_wheel and natal_wheel.chart_url:
            chart_svg = await self._download_chart_svg(natal_wheel.chart_url)

        planets = safe(results[1])
        planets_extended = safe(results[2])
        _normalize_planet_names(planets)
        _normalize_planet_names(planets_extended)

        houses = safe(results[3])
        if houses is None and planets is not None:
            houses = self._houses_from_planets(planets)

        return KundliData(
            request=request,
            birth_details=safe(results[0]),
            planets=planets,
            planets_extended=planets_extended,
            houses=houses,
            horo_chart_d1=safe(results[4]),
            natal_wheel_chart=natal_wheel,
            natal_chart_svg=chart_svg,
            panchang=safe(results[6]),
            current_vdasha=current_vdasha,
            major_vdasha=safe(results[8]),
            kp_birth_chart=safe(results[9]),
            sarvashtak=safe(results[10]),
            ayanamsha_details=safe(results[11]),
            astro_details=safe(results[12]),
            ghat_chakra=safe(results[13]),
            bhav_madhya=safe(results[14]),
            planet_nature=safe(results[15]),
            panchada_maitri=safe(results[16]),
            horo_chart_extended=safe(results[17]),
            planet_ashtak=planet_ashtak or None,
            horo_charts=horo_charts or None,
            horo_chart_images=horo_chart_images or None,
            general_ascendant_report=safe(results[18]),
            general_nakshatra_report=safe(results[19]),
            general_house_reports=general_house_reports or None,
            general_rashi_reports=general_rashi_reports or None,
            simple_manglik=safe(results[20]),
            manglik=safe(results[21]),
            kalsarpa_details=safe(results[22]),
            sadhesati_current_status=safe(results[23]),
            sadhesati_life_details=safe(results[24]),
            pitra_dosha_report=safe(results[25]),
            puja_suggestion=safe(results[26]),
            basic_gem_suggestion=safe(results[27]),
            rudraksha_suggestion=safe(results[28]),
            sadhesati_remedies=safe(results[29]),
            daily_nakshatra_prediction=safe(results[30]),
            daily_nakshatra_prediction_next=safe(results[31]),
            daily_nakshatra_prediction_previous=safe(results[32]),
            varshaphal_year_chart=safe(results[33]),
            varshaphal_month_chart=safe(results[34]),
            varshaphal_details=safe(results[35]),
            varshaphal_planets=safe(results[36]),
            varshaphal_muntha=safe(results[37]),
            varshaphal_mudda_dasha=safe(results[38]),
            varshaphal_panchavargeeya_bala=safe(results[39]),
            varshaphal_harsha_bala=safe(results[40]),
            varshaphal_saham_points=safe(results[41]),
            varshaphal_yoga=safe(results[42]),
            current_vdasha_all=safe(results[43]),
            sub_vdasha=sub_vdasha_data,
            sub_sub_vdasha=sub_sub_vdasha_data,
            sub_sub_sub_vdasha=sub_sub_sub_vdasha_data,
            sub_sub_sub_sub_vdasha=sub_sub_sub_sub_vdasha_data,
            kp_planets=safe(results[44]),
            kp_house_cusps=safe(results[45]),
            kp_house_significator=safe(results[46]),
            kp_planet_significator=safe(results[47]),
            major_yogini_dasha=safe(results[48]),
            current_yogini_dasha=safe(results[49]),
            sub_yogini_dasha=safe(results[50]),
            basic_panchang=safe(results[51]),
            basic_panchang_sunrise=safe(results[52]),
            advanced_panchang_sunrise=safe(results[53]),
            planet_panchang=safe(results[54]),
            planet_panchang_sunrise=safe(results[55]),
            chaughadiya_muhurta=safe(results[56]),
            hora_muhurta=safe(results[57]),
            hora_muhurta_dinman=safe(results[58]),
            panchang_chart=safe(results[59]),
            tamil_month_panchang=safe(results[60]),
            tamil_panchang=safe(results[61]),
            panchang_festival=safe(results[62]),
            # Char Dasha
            current_chardasha=current_chardasha_data,
            major_chardasha=safe(results[64]),
            sub_chardasha=sub_chardasha_data,
            # Numerology
            numero_table=safe(results[65]),
            numero_report=safe(results[66]),
            numero_fav_time=safe(results[67]),
            numero_place_vastu=safe(results[68]),
            numero_fasts_report=safe(results[69]),
            numero_fav_lord=safe(results[70]),
            numero_fav_mantra=safe(results[71]),
            numero_prediction_daily=safe(results[72]),
            # Lal Kitab
            lalkitab_horoscope=safe(results[73]),
            lalkitab_planets=safe(results[74]),
            lalkitab_houses=safe(results[75]),
            lalkitab_debts=safe(results[76]),
            lalkitab_remedies=lalkitab_remedies or None,
            # KP Extended
            kp_horoscope=safe(results[77]),
            # Biorhythm
            biorhythm=safe(results[78]),
            moon_biorhythm=safe(results[79]),
            # Monthly Panchang
            monthly_panchang=safe(results[80]),
        )

    @staticmethod
    def _houses_from_planets(planets: list[PlanetData]) -> list[HouseData]:
        sign_order = list(SIGN_LORDS.keys())
        asc = next((p for p in planets if p.name == "Ascendant"), None)
        if asc and asc.sign in sign_order:
            start_idx = sign_order.index(asc.sign)
        else:
            house_signs: dict[int, str] = {}
            for p in planets:
                if p.house and p.sign and p.house not in house_signs:
                    house_signs[p.house] = p.sign
            houses: list[HouseData] = []
            for i in range(1, 13):
                sign = house_signs.get(i, "")
                houses.append(HouseData(
                    house_id=i, sign=sign, sign_id=0, degree=0.0,
                    sign_lord=SIGN_LORDS.get(sign, ""),
                ))
            return houses

        houses: list[HouseData] = []
        for i in range(12):
            idx = (start_idx + i) % 12
            sign = sign_order[idx]
            houses.append(HouseData(
                house_id=i + 1,
                sign=sign,
                sign_id=idx + 1,
                degree=0.0,
                sign_lord=SIGN_LORDS.get(sign, ""),
            ))
        return houses

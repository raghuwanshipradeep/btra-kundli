from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KundliRequest(BaseModel):
    name: str = "Native"
    day: int
    month: int
    year: int
    hour: int
    min: int
    lat: float
    lon: float
    tzone: float
    lang: str = "en"
    place: str = ""
    report_tier: str = "detailed"


class BirthDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")

    year: int = 0
    month: int = 0
    day: int = 0
    hour: int = 0
    minute: int = 0
    latitude: float = 0.0
    longitude: float = 0.0
    timezone: float = 0.0
    sunrise: str = ""
    sunset: str = ""
    ayanamsha: float = Field(0.0, alias="ayanamsha")


class PlanetData(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: int = 0
    name: str = ""
    fullDegree: float = Field(0.0, alias="fullDegree")
    normDegree: float = Field(0.0, alias="normDegree")
    speed: float = 0.0
    sign: str = ""
    signLord: str = Field("", alias="signLord")
    nakshatra: str = ""
    nakshatraLord: str = Field("", alias="nakshatraLord")
    nakshatra_pad: int = Field(0, alias="nakshatra_pad")
    house: int = 0
    isRetro: str = Field("false", alias="isRetro")
    is_planet_set: bool = Field(False, alias="is_planet_set")
    planet_awastha: str = Field("", alias="planet_awastha")

    @field_validator("isRetro", mode="before")
    @classmethod
    def coerce_retro(cls, v: Any) -> str:
        if isinstance(v, bool):
            return "true" if v else "false"
        return str(v)


class HoroChartSign(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sign: int = 0
    sign_name: str = ""
    planet: list[str] = Field(default_factory=list)
    planet_small: list[str] = Field(default_factory=list)
    planet_degree: list[str] = Field(default_factory=list)


class NatalWheelChart(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: bool = False
    chart_url: str = ""
    msg: str = ""


class TithiDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    details: dict = Field(default_factory=dict)
    end_time: dict = Field(default_factory=dict)
    end_time_ms: float = 0.0


class NakshatraDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    details: dict = Field(default_factory=dict)
    end_time: dict = Field(default_factory=dict)
    end_time_ms: float = 0.0


class PanchangResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    day: str = ""
    sunrise: str = ""
    sunset: str = ""
    moonrise: str = ""
    moonset: str = ""
    vedic_sunrise: str = ""
    vedic_sunset: str = ""
    tithi: dict = Field(default_factory=dict)
    nakshatra: dict = Field(default_factory=dict)
    yog: dict = Field(default_factory=dict)
    karan: dict = Field(default_factory=dict)
    hindu_maah: dict = Field(default_factory=dict)
    paksha: str = ""
    ritu: str = ""
    sun_sign: str = ""
    moon_sign: str = ""
    ayanamsha: float = 0.0
    obliquity: float = 0.0
    sun_last_entry: dict = Field(default_factory=dict)
    sun_next_entry: dict = Field(default_factory=dict)


class DashaPeriodLevel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    planet: str = ""
    planet_id: int = 0
    start: str = ""
    end: str = ""


class CurrentDasha(BaseModel):
    model_config = ConfigDict(extra="ignore")

    major: DashaPeriodLevel = Field(default_factory=DashaPeriodLevel)
    minor: DashaPeriodLevel = Field(default_factory=DashaPeriodLevel)
    sub_minor: DashaPeriodLevel = Field(default_factory=DashaPeriodLevel)
    sub_sub_minor: DashaPeriodLevel = Field(default_factory=DashaPeriodLevel)
    sub_sub_sub_minor: DashaPeriodLevel = Field(default_factory=DashaPeriodLevel)


class DashaPeriod(BaseModel):
    model_config = ConfigDict(extra="ignore")

    planet: str = ""
    planet_id: int = 0
    start: str = ""
    end: str = ""


class KPHouseData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    signs: list[int] = Field(default_factory=list)
    planets: list[str] = Field(default_factory=list)
    planets_small: list[str] = Field(default_factory=list)
    planet_signs: list[int] = Field(default_factory=list)


class AshtakVargaSign(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sign: str = ""
    sign_id: int = 0
    sun_points: int = 0
    moon_points: int = 0
    mars_points: int = 0
    mercury_points: int = 0
    jupiter_points: int = 0
    venus_points: int = 0
    saturn_points: int = 0
    ascendant_points: int = 0
    total_points: int = 0


class HouseData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    house_id: int = 0
    sign: str = ""
    sign_id: int = 0
    degree: float = 0.0
    sign_lord: str = ""


class GeoName(BaseModel):
    model_config = ConfigDict(extra="ignore")

    place_name: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    country_code: str = ""
    timezone_id: str = ""

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def coerce_float(cls, v: Any) -> float:
        return float(v) if isinstance(v, str) else v


class AyanamshaEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str = ""
    degree: float = 0.0
    formatted: str = ""


class AstroDetails(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    ascendant: str = ""
    ascendant_lord: str = ""
    Varna: str = ""
    Vashya: str = ""
    Yoni: str = ""
    Gan: str = ""
    Nadi: str = ""
    SignLord: str = ""
    sign: str = ""
    Naksahtra: str = ""
    NaksahtraLord: str = ""
    Charan: int = 0
    Yog: str = ""
    Karan: str = ""
    Tithi: str = ""
    yunja: str = ""
    tatva: str = ""
    name_alphabet: str = ""
    paya: str = ""


class GhatChakra(BaseModel):
    model_config = ConfigDict(extra="ignore")

    month: str = ""
    tithi: str = ""
    day: str = ""
    nakshatra: str = ""
    yog: str = ""
    karan: str = ""
    pahar: str = ""
    moon: str = ""


class BhavMadhyaEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    house: int = 0
    degree: float = 0.0
    sign: str = ""
    norm_degree: float = 0.0
    sign_id: int = 0


class BhavMadhya(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ascendant: float = 0.0
    midheaven: float = 0.0
    ayanamsha: float = 0.0
    bhav_madhya: list[BhavMadhyaEntry] = Field(default_factory=list)
    bhav_sandhi: list[BhavMadhyaEntry] = Field(default_factory=list)


class PlanetNature(BaseModel):
    model_config = ConfigDict(extra="ignore")

    GOOD: list[str] = Field(default_factory=list)
    BAD: list[str] = Field(default_factory=list)
    KILLER: list[str] = Field(default_factory=list)
    YOGAKARAKA: list[str] = Field(default_factory=list)


class PlanetAshtakVarga(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ashtak_varga: dict = Field(default_factory=dict)
    ashtak_points: dict = Field(default_factory=dict)


class KundliData(BaseModel):
    request: KundliRequest
    birth_details: BirthDetails | None = None
    planets: list[PlanetData] | None = None
    planets_extended: list[PlanetData] | None = None
    houses: list[HouseData] | None = None
    horo_chart_d1: list[HoroChartSign] | None = None
    natal_wheel_chart: NatalWheelChart | None = None
    natal_chart_svg: str | None = None
    panchang: PanchangResponse | None = None
    basic_panchang: dict | list | None = None
    basic_panchang_sunrise: dict | list | None = None
    advanced_panchang_sunrise: dict | list | None = None
    planet_panchang: dict | list | None = None
    planet_panchang_sunrise: dict | list | None = None
    chaughadiya_muhurta: dict | list | None = None
    hora_muhurta: dict | list | None = None
    hora_muhurta_dinman: dict | list | None = None
    panchang_chart: dict | list | None = None
    tamil_month_panchang: dict | list | None = None
    tamil_panchang: dict | list | None = None
    panchang_festival: dict | list | None = None
    current_vdasha: CurrentDasha | None = None
    major_vdasha: list[DashaPeriod] | None = None
    kp_birth_chart: list[KPHouseData] | None = None
    sarvashtak: list[AshtakVargaSign] | None = None
    ayanamsha_details: list[AyanamshaEntry] | None = None
    astro_details: AstroDetails | None = None
    ghat_chakra: GhatChakra | None = None
    bhav_madhya: BhavMadhya | None = None
    planet_nature: PlanetNature | None = None
    panchada_maitri: dict | None = None
    planet_ashtak: dict[str, PlanetAshtakVarga] | None = None
    horo_charts: dict[str, list[HoroChartSign]] | None = None
    horo_chart_images: dict[str, str] | None = None
    horo_chart_extended: dict | None = None
    general_house_reports: dict[str, dict] | None = None
    general_rashi_reports: dict[str, dict] | None = None
    general_ascendant_report: dict | None = None
    general_nakshatra_report: dict | None = None
    simple_manglik: dict | None = None
    manglik: dict | None = None
    kalsarpa_details: dict | None = None
    sadhesati_current_status: dict | None = None
    sadhesati_life_details: dict | list | None = None
    pitra_dosha_report: dict | None = None
    puja_suggestion: dict | None = None
    basic_gem_suggestion: dict | None = None
    rudraksha_suggestion: dict | None = None
    sadhesati_remedies: dict | None = None
    daily_nakshatra_prediction: dict | None = None
    daily_nakshatra_prediction_next: dict | None = None
    daily_nakshatra_prediction_previous: dict | None = None
    varshaphal_year_chart: dict | None = None
    varshaphal_month_chart: dict | None = None
    varshaphal_details: dict | None = None
    varshaphal_planets: dict | list | None = None
    varshaphal_muntha: dict | None = None
    varshaphal_mudda_dasha: dict | None = None
    varshaphal_panchavargeeya_bala: dict | None = None
    varshaphal_harsha_bala: dict | None = None
    varshaphal_saham_points: dict | None = None
    varshaphal_yoga: dict | list | None = None
    current_vdasha_all: dict | None = None
    sub_vdasha: list | None = None
    sub_sub_vdasha: list | None = None
    sub_sub_sub_vdasha: list | None = None
    sub_sub_sub_sub_vdasha: list | None = None
    kp_planets: list | None = None
    kp_house_cusps: list | None = None
    kp_house_significator: dict | list | None = None
    kp_planet_significator: dict | list | None = None
    major_yogini_dasha: list | None = None
    current_yogini_dasha: dict | None = None
    sub_yogini_dasha: list | None = None

    # Char (Jaimini) Dasha
    current_chardasha: dict | None = None
    major_chardasha: list | None = None
    sub_chardasha: list | None = None

    # Numerology
    numero_table: dict | None = None
    numero_report: dict | None = None
    numero_fav_time: dict | None = None
    numero_place_vastu: dict | None = None
    numero_fasts_report: dict | None = None
    numero_fav_lord: dict | None = None
    numero_fav_mantra: dict | None = None
    numero_prediction_daily: dict | None = None

    # Lal Kitab
    lalkitab_horoscope: dict | list | None = None
    lalkitab_planets: dict | list | None = None
    lalkitab_houses: dict | list | None = None
    lalkitab_debts: dict | list | None = None
    lalkitab_remedies: dict[str, dict] | None = None

    # KP Extended
    kp_horoscope: dict | None = None

    # Biorhythm
    biorhythm: dict | None = None
    moon_biorhythm: dict | None = None

    # Monthly Panchang
    monthly_panchang: dict | list | None = None

    # LLM Narratives (populated by narrative_engine before PDF generation)
    narratives: dict[str, str] = Field(default_factory=dict)


class MatchRequest(BaseModel):
    m_name: str = "Groom"
    m_day: int
    m_month: int
    m_year: int
    m_hour: int
    m_min: int
    m_lat: float
    m_lon: float
    m_tzone: float
    f_name: str = "Bride"
    f_day: int
    f_month: int
    f_year: int
    f_hour: int
    f_min: int
    f_lat: float
    f_lon: float
    f_tzone: float
    lang: str = "en"


class MatchData(BaseModel):
    request: MatchRequest
    match_birth_details: dict | None = None
    match_astro_details: dict | None = None
    match_planet_details: dict | None = None
    match_obstructions: dict | None = None
    match_manglik_report: dict | None = None
    match_ashtakoot_points: dict | None = None
    match_dashakoot_points: dict | None = None
    match_percentage: dict | None = None
    match_report: dict | None = None
    match_detailed_report: dict | None = None

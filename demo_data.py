from models import (
    AshtakVargaSign,
    AstroDetails,
    AyanamshaEntry,
    BhavMadhya,
    BhavMadhyaEntry,
    BirthDetails,
    CurrentDasha,
    DashaPeriod,
    DashaPeriodLevel,
    GhatChakra,
    HoroChartSign,
    HouseData,
    KPHouseData,
    KundliData,
    KundliRequest,
    PanchangResponse,
    PlanetAshtakVarga,
    PlanetData,
    PlanetNature,
)

SAMPLE_REQUEST = KundliRequest(
    name="Rahul Sharma",
    day=15,
    month=8,
    year=1990,
    hour=14,
    min=30,
    lat=23.1765,
    lon=75.7885,
    tzone=5.5,
    lang="en",
)

SAMPLE_BIRTH_DETAILS = BirthDetails(
    year=1990,
    month=8,
    day=15,
    hour=14,
    minute=30,
    latitude=23.1765,
    longitude=75.7885,
    timezone=5.5,
    sunrise="06:05:42",
    sunset="19:06:18",
    ayanamsha=23.722356,
)

SAMPLE_PLANETS = [
    PlanetData(id=0, name="Ascendant", fullDegree=236.45, normDegree=26.45, speed=0.0, sign="Scorpio", signLord="Mars", nakshatra="Jyeshtha", nakshatraLord="Mercury", nakshatra_pad=3, house=1, isRetro="false"),
    PlanetData(id=1, name="Sun", fullDegree=118.92, normDegree=28.92, speed=0.96, sign="Cancer", signLord="Moon", nakshatra="Ashlesha", nakshatraLord="Mercury", nakshatra_pad=4, house=9, isRetro="false"),
    PlanetData(id=2, name="Moon", fullDegree=325.18, normDegree=25.18, speed=13.2, sign="Aquarius", signLord="Saturn", nakshatra="Purva Bhadrapada", nakshatraLord="Jupiter", nakshatra_pad=4, house=4, isRetro="false"),
    PlanetData(id=3, name="Mars", fullDegree=56.33, normDegree=26.33, speed=0.62, sign="Taurus", signLord="Venus", nakshatra="Mrigashira", nakshatraLord="Mars", nakshatra_pad=1, house=7, isRetro="false"),
    PlanetData(id=4, name="Mercury", fullDegree=132.76, normDegree=12.76, speed=1.82, sign="Leo", signLord="Sun", nakshatra="Magha", nakshatraLord="Ketu", nakshatra_pad=4, house=10, isRetro="false"),
    PlanetData(id=5, name="Jupiter", fullDegree=88.41, normDegree=28.41, speed=0.12, sign="Gemini", signLord="Mercury", nakshatra="Punarvasu", nakshatraLord="Jupiter", nakshatra_pad=3, house=8, isRetro="false"),
    PlanetData(id=6, name="Venus", fullDegree=104.55, normDegree=14.55, speed=1.24, sign="Cancer", signLord="Moon", nakshatra="Pushya", nakshatraLord="Saturn", nakshatra_pad=2, house=9, isRetro="false"),
    PlanetData(id=7, name="Saturn", fullDegree=279.82, normDegree=9.82, speed=-0.08, sign="Capricorn", signLord="Saturn", nakshatra="Uttara Ashadha", nakshatraLord="Sun", nakshatra_pad=3, house=3, isRetro="true"),
    PlanetData(id=8, name="Rahu", fullDegree=289.15, normDegree=19.15, speed=-0.05, sign="Capricorn", signLord="Saturn", nakshatra="Shravana", nakshatraLord="Moon", nakshatra_pad=3, house=3, isRetro="true"),
    PlanetData(id=9, name="Ketu", fullDegree=109.15, normDegree=19.15, speed=-0.05, sign="Cancer", signLord="Moon", nakshatra="Ashlesha", nakshatraLord="Mercury", nakshatra_pad=1, house=9, isRetro="true"),
    PlanetData(id=10, name="Uranus", fullDegree=276.50, normDegree=6.50, speed=0.012, sign="Capricorn", signLord="Saturn", nakshatra="Uttara Ashadha", nakshatraLord="Sun", nakshatra_pad=2, house=3, isRetro="false"),
    PlanetData(id=11, name="Neptune", fullDegree=280.15, normDegree=10.15, speed=0.006, sign="Capricorn", signLord="Saturn", nakshatra="Shravana", nakshatraLord="Moon", nakshatra_pad=1, house=3, isRetro="false"),
    PlanetData(id=12, name="Pluto", fullDegree=233.80, normDegree=23.80, speed=0.003, sign="Scorpio", signLord="Mars", nakshatra="Jyeshtha", nakshatraLord="Mercury", nakshatra_pad=2, house=1, isRetro="true"),
]

SAMPLE_HOUSES = [
    HouseData(house_id=1, sign="Scorpio", sign_id=8, degree=236.45, sign_lord="Mars"),
    HouseData(house_id=2, sign="Sagittarius", sign_id=9, degree=265.12, sign_lord="Jupiter"),
    HouseData(house_id=3, sign="Capricorn", sign_id=10, degree=295.33, sign_lord="Saturn"),
    HouseData(house_id=4, sign="Aquarius", sign_id=11, degree=325.55, sign_lord="Saturn"),
    HouseData(house_id=5, sign="Pisces", sign_id=12, degree=355.22, sign_lord="Jupiter"),
    HouseData(house_id=6, sign="Aries", sign_id=1, degree=25.44, sign_lord="Mars"),
    HouseData(house_id=7, sign="Taurus", sign_id=2, degree=56.45, sign_lord="Venus"),
    HouseData(house_id=8, sign="Gemini", sign_id=3, degree=85.12, sign_lord="Mercury"),
    HouseData(house_id=9, sign="Cancer", sign_id=4, degree=115.33, sign_lord="Moon"),
    HouseData(house_id=10, sign="Leo", sign_id=5, degree=145.55, sign_lord="Sun"),
    HouseData(house_id=11, sign="Virgo", sign_id=6, degree=175.22, sign_lord="Mercury"),
    HouseData(house_id=12, sign="Libra", sign_id=7, degree=205.44, sign_lord="Venus"),
]

SAMPLE_HORO_CHART = [
    HoroChartSign(sign=1, sign_name="Aries", planet=[], planet_small=[]),
    HoroChartSign(sign=2, sign_name="Taurus", planet=["Mars"], planet_small=["Ma"]),
    HoroChartSign(sign=3, sign_name="Gemini", planet=["Jupiter"], planet_small=["Ju"]),
    HoroChartSign(sign=4, sign_name="Cancer", planet=["Sun", "Venus", "Ketu"], planet_small=["Su", "Ve", "Ke"]),
    HoroChartSign(sign=5, sign_name="Leo", planet=["Mercury"], planet_small=["Me"]),
    HoroChartSign(sign=6, sign_name="Virgo", planet=[], planet_small=[]),
    HoroChartSign(sign=7, sign_name="Libra", planet=[], planet_small=[]),
    HoroChartSign(sign=8, sign_name="Scorpio", planet=["Ascendant"], planet_small=["As"]),
    HoroChartSign(sign=9, sign_name="Sagittarius", planet=[], planet_small=[]),
    HoroChartSign(sign=10, sign_name="Capricorn", planet=["Saturn", "Rahu"], planet_small=["Sa", "Ra"]),
    HoroChartSign(sign=11, sign_name="Aquarius", planet=["Moon"], planet_small=["Mo"]),
    HoroChartSign(sign=12, sign_name="Pisces", planet=[], planet_small=[]),
]

SAMPLE_PANCHANG = PanchangResponse(
    day="Wednesday",
    sunrise="06:05:42",
    sunset="19:06:18",
    moonrise="22:15:33",
    moonset="09:45:12",
    vedic_sunrise="05:58:22",
    vedic_sunset="19:13:38",
    tithi={
        "details": {"tithi_name": "Krishna Dashami", "tithi_number": 25, "deity": "Dharmaraja"},
        "end_time": {"hour": 18, "minute": 32, "second": 15},
    },
    nakshatra={
        "details": {"nak_name": "Purva Bhadrapada", "ruler": "Jupiter", "deity": "Aja Ekapad"},
        "end_time": {"hour": 14, "minute": 22, "second": 8},
    },
    yog={"details": {"yog_name": "Shubha", "meaning": "Auspicious"}},
    karan={"details": {"karan_name": "Taitil", "deity": "Naga"}},
    paksha="Krishna",
    ritu="Varsha",
    sun_sign="Cancer",
    moon_sign="Aquarius",
    ayanamsha=23.722356,
)

SAMPLE_BASIC_PANCHANG = {
    "day": "Wednesday",
    "sunrise": "06:05:42",
    "sunset": "19:06:18",
    "tithi": {"tithi_name": "Krishna Dashami", "tithi_number": 25},
    "nakshatra": {"nakshatra_name": "Purva Bhadrapada", "nakshatra_number": 25},
    "yog": {"yog_name": "Shubha"},
    "karan": {"karan_name": "Taitil"},
    "paksha": "Krishna",
    "ritu": "Varsha",
    "sun_sign": "Cancer",
    "moon_sign": "Aquarius",
}

SAMPLE_CHAUGHADIYA = {
    "chaughadiya": {
        "day": [
            {"time": "06:05 - 07:34", "muhurta": "Udveg", "type": "Inauspicious"},
            {"time": "07:34 - 09:03", "muhurta": "Chal", "type": "Good"},
            {"time": "09:03 - 10:32", "muhurta": "Labh", "type": "Profitable"},
            {"time": "10:32 - 12:01", "muhurta": "Amrit", "type": "Best"},
            {"time": "12:01 - 13:30", "muhurta": "Kaal", "type": "Inauspicious"},
            {"time": "13:30 - 14:59", "muhurta": "Shubh", "type": "Auspicious"},
            {"time": "14:59 - 16:28", "muhurta": "Rog", "type": "Inauspicious"},
            {"time": "16:28 - 19:06", "muhurta": "Udveg", "type": "Inauspicious"},
        ],
        "night": [
            {"time": "19:06 - 20:35", "muhurta": "Shubh", "type": "Auspicious"},
            {"time": "20:35 - 22:04", "muhurta": "Amrit", "type": "Best"},
            {"time": "22:04 - 23:33", "muhurta": "Chal", "type": "Good"},
            {"time": "23:33 - 01:02", "muhurta": "Rog", "type": "Inauspicious"},
            {"time": "01:02 - 02:31", "muhurta": "Kaal", "type": "Inauspicious"},
            {"time": "02:31 - 04:00", "muhurta": "Labh", "type": "Profitable"},
            {"time": "04:00 - 05:29", "muhurta": "Udveg", "type": "Inauspicious"},
            {"time": "05:29 - 06:05", "muhurta": "Shubh", "type": "Auspicious"},
        ],
    }
}

SAMPLE_HORA_MUHURTA = {
    "hora": [
        {"time": "06:05 - 07:05", "hora_lord": "Mercury"},
        {"time": "07:05 - 08:05", "hora_lord": "Moon"},
        {"time": "08:05 - 09:05", "hora_lord": "Saturn"},
        {"time": "09:05 - 10:05", "hora_lord": "Jupiter"},
        {"time": "10:05 - 11:05", "hora_lord": "Mars"},
        {"time": "11:05 - 12:05", "hora_lord": "Sun"},
    ]
}

SAMPLE_PLANET_PANCHANG = {
    "planets": [
        {"planet": "Sun", "sign": "Cancer", "degree": "28°55'12\"", "nakshatra": "Ashlesha"},
        {"planet": "Moon", "sign": "Aquarius", "degree": "25°10'44\"", "nakshatra": "Purva Bhadrapada"},
        {"planet": "Mars", "sign": "Taurus", "degree": "26°19'55\"", "nakshatra": "Mrigashirsha"},
    ]
}

SAMPLE_PANCHANG_FESTIVAL = {
    "festivals": [
        {"name": "Ekadashi", "description": "Fasting day dedicated to Lord Vishnu"},
    ]
}

SAMPLE_PANCHANG_CHART = {
    "chart_url": "https://example.com/panchang_chart.svg",
    "ascendant": "Scorpio",
}

SAMPLE_CURRENT_DASHA = CurrentDasha(
    major=DashaPeriodLevel(planet="Mercury", planet_id=4, start="16-8-2012 14:30", end="16-8-2029 14:30"),
    minor=DashaPeriodLevel(planet="Saturn", planet_id=7, start="25-4-2025 08:15", end="4-1-2028 20:45"),
    sub_minor=DashaPeriodLevel(planet="Jupiter", planet_id=5, start="10-3-2026 12:00", end="22-8-2026 06:30"),
    sub_sub_minor=DashaPeriodLevel(planet="Mars", planet_id=3, start="1-5-2026 09:00", end="19-5-2026 15:30"),
    sub_sub_sub_minor=DashaPeriodLevel(planet="Venus", planet_id=6, start="8-5-2026 06:00", end="11-5-2026 18:00"),
)

SAMPLE_MAJOR_VDASHA = [
    DashaPeriod(planet="Ketu", planet_id=8, start="15-8-1990 14:30", end="15-8-1997 14:30"),
    DashaPeriod(planet="Venus", planet_id=6, start="15-8-1997 14:30", end="15-8-2017 14:30"),
    DashaPeriod(planet="Sun", planet_id=1, start="15-8-2017 14:30", end="15-8-2023 14:30"),
    DashaPeriod(planet="Moon", planet_id=2, start="15-8-2023 14:30", end="15-8-2033 14:30"),
    DashaPeriod(planet="Mars", planet_id=3, start="15-8-2033 14:30", end="15-8-2040 14:30"),
    DashaPeriod(planet="Rahu", planet_id=7, start="15-8-2040 14:30", end="15-8-2058 14:30"),
    DashaPeriod(planet="Jupiter", planet_id=5, start="15-8-2058 14:30", end="15-8-2074 14:30"),
    DashaPeriod(planet="Saturn", planet_id=6, start="15-8-2074 14:30", end="15-8-2093 14:30"),
    DashaPeriod(planet="Mercury", planet_id=4, start="15-8-2093 14:30", end="15-8-2110 14:30"),
]

SAMPLE_KP_CHART = [
    KPHouseData(signs=[8, 9], planets=["Ascendant"], planets_small=["As"], planet_signs=[8]),
    KPHouseData(signs=[9], planets=[], planets_small=[], planet_signs=[]),
    KPHouseData(signs=[10], planets=["Saturn", "Rahu"], planets_small=["Sa", "Ra"], planet_signs=[10, 10]),
    KPHouseData(signs=[11], planets=["Moon"], planets_small=["Mo"], planet_signs=[11]),
    KPHouseData(signs=[12], planets=[], planets_small=[], planet_signs=[]),
    KPHouseData(signs=[1], planets=[], planets_small=[], planet_signs=[]),
    KPHouseData(signs=[2], planets=["Mars"], planets_small=["Ma"], planet_signs=[2]),
    KPHouseData(signs=[3], planets=["Jupiter"], planets_small=["Ju"], planet_signs=[3]),
    KPHouseData(signs=[4], planets=["Sun", "Venus", "Ketu"], planets_small=["Su", "Ve", "Ke"], planet_signs=[4, 4, 4]),
    KPHouseData(signs=[5], planets=["Mercury"], planets_small=["Me"], planet_signs=[5]),
    KPHouseData(signs=[6], planets=[], planets_small=[], planet_signs=[]),
    KPHouseData(signs=[7], planets=[], planets_small=[], planet_signs=[]),
]

SAMPLE_SARVASHTAK = [
    AshtakVargaSign(sign="Aries", sign_id=1, sun_points=5, moon_points=4, mars_points=3, mercury_points=5, jupiter_points=6, venus_points=4, saturn_points=3, ascendant_points=4, total_points=34),
    AshtakVargaSign(sign="Taurus", sign_id=2, sun_points=3, moon_points=5, mars_points=2, mercury_points=4, jupiter_points=4, venus_points=5, saturn_points=4, ascendant_points=3, total_points=30),
    AshtakVargaSign(sign="Gemini", sign_id=3, sun_points=4, moon_points=3, mars_points=4, mercury_points=6, jupiter_points=5, venus_points=3, saturn_points=2, ascendant_points=5, total_points=32),
    AshtakVargaSign(sign="Cancer", sign_id=4, sun_points=6, moon_points=5, mars_points=3, mercury_points=4, jupiter_points=4, venus_points=6, saturn_points=3, ascendant_points=4, total_points=35),
    AshtakVargaSign(sign="Leo", sign_id=5, sun_points=5, moon_points=4, mars_points=5, mercury_points=5, jupiter_points=3, venus_points=4, saturn_points=4, ascendant_points=3, total_points=33),
    AshtakVargaSign(sign="Virgo", sign_id=6, sun_points=3, moon_points=3, mars_points=2, mercury_points=4, jupiter_points=5, venus_points=3, saturn_points=5, ascendant_points=4, total_points=29),
    AshtakVargaSign(sign="Libra", sign_id=7, sun_points=4, moon_points=4, mars_points=4, mercury_points=3, jupiter_points=4, venus_points=5, saturn_points=3, ascendant_points=5, total_points=32),
    AshtakVargaSign(sign="Scorpio", sign_id=8, sun_points=5, moon_points=5, mars_points=5, mercury_points=5, jupiter_points=6, venus_points=4, saturn_points=4, ascendant_points=4, total_points=38),
    AshtakVargaSign(sign="Sagittarius", sign_id=9, sun_points=4, moon_points=3, mars_points=3, mercury_points=4, jupiter_points=5, venus_points=3, saturn_points=3, ascendant_points=3, total_points=28),
    AshtakVargaSign(sign="Capricorn", sign_id=10, sun_points=3, moon_points=4, mars_points=4, mercury_points=3, jupiter_points=3, venus_points=4, saturn_points=5, ascendant_points=4, total_points=30),
    AshtakVargaSign(sign="Aquarius", sign_id=11, sun_points=4, moon_points=5, mars_points=3, mercury_points=5, jupiter_points=4, venus_points=5, saturn_points=4, ascendant_points=3, total_points=33),
    AshtakVargaSign(sign="Pisces", sign_id=12, sun_points=3, moon_points=4, mars_points=4, mercury_points=3, jupiter_points=5, venus_points=4, saturn_points=2, ascendant_points=4, total_points=29),
]

SAMPLE_AYANAMSHA = [
    AyanamshaEntry(type="LAHIRI", degree=23.722362954519497, formatted="23:43:20"),
    AyanamshaEntry(type="KP", degree=23.625510629241660, formatted="23:37:31"),
    AyanamshaEntry(type="YUKTESHWAR", degree=22.344073616723335, formatted="22:20:38"),
    AyanamshaEntry(type="RAMAN", degree=22.276061629241667, formatted="22:16:33"),
    AyanamshaEntry(type="JN_BHASIN", degree=22.627407616723360, formatted="22:37:38"),
    AyanamshaEntry(type="FAGAN_BRADLEY", degree=24.605570593823188, formatted="24:36:20"),
]

SAMPLE_ASTRO_DETAILS = AstroDetails(
    ascendant="Scorpio",
    ascendant_lord="Mars",
    Varna="Brahmin",
    Vashya="Keeta",
    Yoni="Nakul",
    Gan="Dev",
    Nadi="Madhya",
    SignLord="Mars",
    sign="Aquarius",
    Naksahtra="Purva Bhadrapada",
    NaksahtraLord="Jupiter",
    Charan=4,
    Yog="Shubha",
    Karan="Taitil",
    Tithi="Krishna Dashami",
    yunja="Madhya",
    tatva="Air",
    name_alphabet="So",
    paya="Silver",
)

SAMPLE_GHAT_CHAKRA = GhatChakra(
    month="Bhadrapada",
    tithi="1,6,11",
    day="Wednesday",
    nakshatra="Purva Bhadrapada",
    yog="Vyatipaat",
    karan="Gara",
    pahar="3",
    moon="9",
)

SAMPLE_BHAV_MADHYA = BhavMadhya(
    ascendant=236.45,
    midheaven=145.55,
    ayanamsha=-23.722362,
    bhav_madhya=[
        BhavMadhyaEntry(house=1, degree=236.45, sign="Scorpio", norm_degree=26.45, sign_id=8),
        BhavMadhyaEntry(house=2, degree=265.12, sign="Sagittarius", norm_degree=25.12, sign_id=9),
        BhavMadhyaEntry(house=3, degree=295.33, sign="Capricorn", norm_degree=25.33, sign_id=10),
        BhavMadhyaEntry(house=4, degree=325.55, sign="Aquarius", norm_degree=25.55, sign_id=11),
        BhavMadhyaEntry(house=5, degree=355.22, sign="Pisces", norm_degree=25.22, sign_id=12),
        BhavMadhyaEntry(house=6, degree=25.44, sign="Aries", norm_degree=25.44, sign_id=1),
        BhavMadhyaEntry(house=7, degree=56.45, sign="Taurus", norm_degree=26.45, sign_id=2),
        BhavMadhyaEntry(house=8, degree=85.12, sign="Gemini", norm_degree=25.12, sign_id=3),
        BhavMadhyaEntry(house=9, degree=115.33, sign="Cancer", norm_degree=25.33, sign_id=4),
        BhavMadhyaEntry(house=10, degree=145.55, sign="Leo", norm_degree=25.55, sign_id=5),
        BhavMadhyaEntry(house=11, degree=175.22, sign="Virgo", norm_degree=25.22, sign_id=6),
        BhavMadhyaEntry(house=12, degree=205.44, sign="Libra", norm_degree=25.44, sign_id=7),
    ],
    bhav_sandhi=[
        BhavMadhyaEntry(house=1, degree=250.78, sign="Sagittarius", norm_degree=10.78, sign_id=9),
        BhavMadhyaEntry(house=2, degree=280.22, sign="Capricorn", norm_degree=10.22, sign_id=10),
        BhavMadhyaEntry(house=3, degree=310.44, sign="Aquarius", norm_degree=10.44, sign_id=11),
        BhavMadhyaEntry(house=4, degree=340.38, sign="Pisces", norm_degree=10.38, sign_id=12),
        BhavMadhyaEntry(house=5, degree=10.33, sign="Aries", norm_degree=10.33, sign_id=1),
        BhavMadhyaEntry(house=6, degree=40.94, sign="Taurus", norm_degree=10.94, sign_id=2),
        BhavMadhyaEntry(house=7, degree=70.78, sign="Gemini", norm_degree=10.78, sign_id=3),
        BhavMadhyaEntry(house=8, degree=100.22, sign="Cancer", norm_degree=10.22, sign_id=4),
        BhavMadhyaEntry(house=9, degree=130.44, sign="Leo", norm_degree=10.44, sign_id=5),
        BhavMadhyaEntry(house=10, degree=160.38, sign="Virgo", norm_degree=10.38, sign_id=6),
        BhavMadhyaEntry(house=11, degree=190.33, sign="Libra", norm_degree=10.33, sign_id=7),
        BhavMadhyaEntry(house=12, degree=220.94, sign="Scorpio", norm_degree=10.94, sign_id=8),
    ],
)

SAMPLE_PLANET_NATURE = PlanetNature(
    GOOD=["Mercury", "Venus"],
    BAD=["Mars", "Moon", "Jupiter", "Sun"],
    KILLER=["Venus"],
    YOGAKARAKA=["Venus"],
)

def _make_ashtak_points(vals: list[int]) -> dict:
    sign_names = [
        "aries", "taurus", "gemini", "cancer", "leo", "virgo",
        "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
    ]
    contributors = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "ascendant"]
    points = {}
    for i, sn in enumerate(sign_names):
        row = {}
        for j, cp in enumerate(contributors):
            row[cp] = (vals[i] + j) % 2
        row["total"] = sum(row[cp] for cp in contributors)
        points[sn] = row
    return points


SAMPLE_PLANET_ASHTAK = {
    planet: PlanetAshtakVarga(
        ashtak_varga={"type": "Bhinnashtak", "planet": planet, "sign": "Scorpio", "sign_id": 8},
        ashtak_points=_make_ashtak_points([i + j for j in range(12)]),
    )
    for i, planet in enumerate(["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"])
}

SAMPLE_HORO_CHARTS = {
    "D9": [
        HoroChartSign(sign=1, sign_name="Aries", planet=["Venus"], planet_small=["Ve"]),
        HoroChartSign(sign=2, sign_name="Taurus", planet=[], planet_small=[]),
        HoroChartSign(sign=3, sign_name="Gemini", planet=["Sun"], planet_small=["Su"]),
        HoroChartSign(sign=4, sign_name="Cancer", planet=["Mercury"], planet_small=["Me"]),
        HoroChartSign(sign=5, sign_name="Leo", planet=[], planet_small=[]),
        HoroChartSign(sign=6, sign_name="Virgo", planet=["Jupiter"], planet_small=["Ju"]),
        HoroChartSign(sign=7, sign_name="Libra", planet=["Ascendant"], planet_small=["As"]),
        HoroChartSign(sign=8, sign_name="Scorpio", planet=["Mars"], planet_small=["Ma"]),
        HoroChartSign(sign=9, sign_name="Sagittarius", planet=[], planet_small=[]),
        HoroChartSign(sign=10, sign_name="Capricorn", planet=["Moon", "Saturn"], planet_small=["Mo", "Sa"]),
        HoroChartSign(sign=11, sign_name="Aquarius", planet=["Rahu"], planet_small=["Ra"]),
        HoroChartSign(sign=12, sign_name="Pisces", planet=["Ketu"], planet_small=["Ke"]),
    ],
    "D3": [
        HoroChartSign(sign=1, sign_name="Aries", planet=["Mars"], planet_small=["Ma"]),
        HoroChartSign(sign=2, sign_name="Taurus", planet=[], planet_small=[]),
        HoroChartSign(sign=3, sign_name="Gemini", planet=["Mercury"], planet_small=["Me"]),
        HoroChartSign(sign=4, sign_name="Cancer", planet=["Moon"], planet_small=["Mo"]),
        HoroChartSign(sign=5, sign_name="Leo", planet=["Sun"], planet_small=["Su"]),
        HoroChartSign(sign=6, sign_name="Virgo", planet=["Ascendant"], planet_small=["As"]),
        HoroChartSign(sign=7, sign_name="Libra", planet=["Venus"], planet_small=["Ve"]),
        HoroChartSign(sign=8, sign_name="Scorpio", planet=[], planet_small=[]),
        HoroChartSign(sign=9, sign_name="Sagittarius", planet=["Jupiter"], planet_small=["Ju"]),
        HoroChartSign(sign=10, sign_name="Capricorn", planet=["Saturn", "Rahu"], planet_small=["Sa", "Ra"]),
        HoroChartSign(sign=11, sign_name="Aquarius", planet=[], planet_small=[]),
        HoroChartSign(sign=12, sign_name="Pisces", planet=["Ketu"], planet_small=["Ke"]),
    ],
}

SAMPLE_PANCHADA_MAITRI = {
    "Sun": {"Moon": "Friend", "Mars": "Friend", "Mercury": "Enemy", "Jupiter": "Friend", "Venus": "Enemy", "Saturn": "Enemy"},
    "Moon": {"Sun": "Friend", "Mars": "Neutral", "Mercury": "Friend", "Jupiter": "Neutral", "Venus": "Neutral", "Saturn": "Neutral"},
    "Mars": {"Sun": "Friend", "Moon": "Friend", "Mercury": "Enemy", "Jupiter": "Friend", "Venus": "Neutral", "Saturn": "Neutral"},
    "Mercury": {"Sun": "Friend", "Moon": "Enemy", "Mars": "Neutral", "Jupiter": "Neutral", "Venus": "Friend", "Saturn": "Neutral"},
    "Jupiter": {"Sun": "Friend", "Moon": "Friend", "Mars": "Friend", "Mercury": "Neutral", "Venus": "Enemy", "Saturn": "Neutral"},
    "Venus": {"Sun": "Enemy", "Moon": "Neutral", "Mars": "Neutral", "Mercury": "Friend", "Jupiter": "Neutral", "Saturn": "Friend"},
    "Saturn": {"Sun": "Enemy", "Moon": "Enemy", "Mars": "Neutral", "Mercury": "Friend", "Jupiter": "Neutral", "Venus": "Friend"},
}

SAMPLE_ASCENDANT_REPORT = {
    "ascendant_report": {
        "ascendant": "Scorpio",
        "report": "The native has Scorpio ascendant which makes them intense, passionate, and determined. Mars as the ascendant lord gives courage and fighting spirit.",
    }
}

SAMPLE_NAKSHATRA_REPORT = {
    "nakshatra_report": {
        "nakshatra": "Purva Bhadrapada",
        "nakshatra_lord": "Jupiter",
        "report": "Born under Purva Bhadrapada nakshatra, the native possesses deep spiritual inclination and philosophical mind.",
    }
}

SAMPLE_HOUSE_REPORTS = {
    "Sun": {"house": 9, "sign": "Cancer", "report": "Sun in the 9th house blesses the native with fortune and spiritual growth."},
    "Moon": {"house": 4, "sign": "Aquarius", "report": "Moon in the 4th house gives emotional connection to home and mother."},
    "Mars": {"house": 7, "sign": "Taurus", "report": "Mars in the 7th house indicates dynamic partnerships."},
    "Mercury": {"house": 10, "sign": "Leo", "report": "Mercury in the 10th house indicates success in communication-related careers."},
    "Jupiter": {"house": 8, "sign": "Gemini", "report": "Jupiter in the 8th house indicates sudden gains through inheritance."},
    "Venus": {"house": 9, "sign": "Cancer", "report": "Venus in the 9th house indicates love for travel and higher learning."},
    "Saturn": {"house": 3, "sign": "Capricorn", "report": "Saturn in the 3rd house makes the native hardworking and determined."},
    "Rahu": {"house": 3, "sign": "Capricorn", "report": "Rahu in the 3rd house gives courage and communication skills."},
    "Ketu": {"house": 9, "sign": "Cancer", "report": "Ketu in the 9th house indicates past-life spiritual merit."},
}

SAMPLE_RASHI_REPORTS = {
    "Sun": {"sign": "Cancer", "report": "Sun in Cancer indicates emotional depth and sensitivity."},
    "Moon": {"sign": "Aquarius", "report": "Moon in Aquarius indicates an innovative and humanitarian nature."},
    "Mars": {"sign": "Taurus", "report": "Mars in Taurus indicates steady determination and material focus."},
    "Mercury": {"sign": "Leo", "report": "Mercury in Leo indicates creative expression and dramatic communication."},
    "Jupiter": {"sign": "Gemini", "report": "Jupiter in Gemini indicates broad intellectual interests."},
    "Venus": {"sign": "Cancer", "report": "Venus in Cancer indicates deep emotional bonds in relationships."},
    "Saturn": {"sign": "Capricorn", "report": "Saturn in Capricorn is in its own sign, giving discipline and ambition."},
    "Rahu": {"sign": "Capricorn", "report": "Rahu in Capricorn amplifies worldly ambitions and career focus."},
    "Ketu": {"sign": "Cancer", "report": "Ketu in Cancer indicates detachment from emotional comforts."},
}

SAMPLE_SIMPLE_MANGLIK = {
    "is_manglik_pitr": False,
    "is_manglik_chandra": False,
    "percentage_manglik_present": 12.5,
    "is_manglik": False,
    "manglik_report": "The native is not Manglik. Mars does not adversely affect the 1st, 4th, 7th, 8th or 12th house from Lagna.",
}

SAMPLE_MANGLIK = {
    "is_manglik_pitr": False,
    "is_manglik_chandra": False,
    "manglik_present_rule": [],
    "manglik_cancel_rule": ["Mars is aspected by Jupiter, canceling Manglik dosha."],
    "percentage_manglik_present": 12.5,
    "percentage_manglik_after_cancellation": 0.0,
    "is_manglik": False,
    "manglik_report": "Mars is placed in the 7th house but its Manglik effect is cancelled by Jupiter's aspect.",
}

SAMPLE_KALSARPA = {
    "present": False,
    "type": "",
    "one_directional": False,
    "report": "Kalsarpa Dosha is not present in this horoscope.",
}

SAMPLE_SADHESATI_STATUS = {
    "is_undergoing_sadhesati": False,
    "sadhesati_status": "Not undergoing Sadhesati",
    "is_undergoing_small_panoti": False,
    "small_panoti_status": "Not undergoing Small Panoti",
}

SAMPLE_SADHESATI_LIFE = {
    "sadhesati_details": [
        {"start": "1997-04-15", "end": "2000-06-20", "phase": "Rising", "saturn_sign": "Aries"},
        {"start": "2027-01-20", "end": "2029-03-25", "phase": "Peak", "saturn_sign": "Aquarius"},
    ]
}

SAMPLE_PITRA_DOSHA = {
    "is_pitra_dosha_present": False,
    "pitra_dosha_report": "No Pitra Dosha found in this horoscope.",
    "remedies": ["Perform Pind Daan during Pitru Paksha."],
}

SAMPLE_PUJA = {
    "puja_list": [
        {"puja_name": "Maha Mrityunjaya Puja", "benefit": "Longevity and health", "deity": "Lord Shiva"},
        {"puja_name": "Navagraha Shanti Puja", "benefit": "Planetary harmony", "deity": "Nine Planets"},
    ]
}

SAMPLE_GEMS = {
    "life_stone": {"name": "Red Coral", "planet": "Mars", "weight": "5-7 carats", "metal": "Gold/Copper"},
    "lucky_stone": {"name": "Yellow Sapphire", "planet": "Jupiter", "weight": "3-5 carats", "metal": "Gold"},
    "fortune_stone": {"name": "Pearl", "planet": "Moon", "weight": "5-7 carats", "metal": "Silver"},
}

SAMPLE_RUDRAKSHA = {
    "rudraksha_suggestion": [
        {"mukhi": 5, "planet": "Jupiter", "benefit": "Knowledge and wisdom"},
        {"mukhi": 3, "planet": "Mars", "benefit": "Courage and confidence"},
    ]
}

SAMPLE_SADHESATI_REMEDIES = {
    "remedies": [
        "Worship Lord Hanuman on Saturdays.",
        "Donate black sesame seeds on Saturdays.",
        "Recite Shani Chalisa regularly.",
    ]
}

SAMPLE_DAILY_PREDICTION = {
    "nakshatra": "Purva Bhadrapada",
    "prediction": {
        "personal": "A productive day with opportunities for growth.",
        "health": "Take care of your diet today.",
        "profession": "Good day for important meetings.",
        "emotions": "Emotional stability will bring peace.",
    }
}

SAMPLE_DAILY_PREDICTION_NEXT = {
    "nakshatra": "Uttara Bhadrapada",
    "prediction": {
        "personal": "Tomorrow brings new beginnings.",
        "health": "A good day for exercise.",
        "profession": "Favorable for starting new projects.",
        "emotions": "You will feel confident and optimistic.",
    }
}

SAMPLE_DAILY_PREDICTION_PREV = {
    "nakshatra": "Shatabhisha",
    "prediction": {
        "personal": "Yesterday was a day for reflection.",
        "health": "Rest was needed and beneficial.",
        "profession": "Past efforts are bearing fruit.",
        "emotions": "Emotional healing was underway.",
    }
}

SAMPLE_VARSHAPHAL_DETAILS = {
    "year": 2026,
    "varshaphal_ascendant": "Leo",
    "muntha_sign": "Aries",
    "varshesh": "Sun",
    "varshesha_strength": "Strong",
}

SAMPLE_VARSHAPHAL_PLANETS = [
    {"name": "Sun", "sign": "Cancer", "degree": 28.92, "retro": False},
    {"name": "Moon", "sign": "Aquarius", "degree": 25.18, "retro": False},
    {"name": "Mars", "sign": "Taurus", "degree": 26.33, "retro": False},
]

SAMPLE_VARSHAPHAL_MUNTHA = {
    "muntha_sign": "Aries",
    "muntha_lord": "Mars",
    "muntha_house": 6,
    "is_benefic": True,
    "report": "Muntha in 6th house indicates victory over enemies and obstacles.",
}

SAMPLE_VARSHAPHAL_YOGA = [
    {"yoga_name": "Ithasala Yoga", "planet1": "Sun", "planet2": "Jupiter", "description": "Beneficial combination for success."},
    {"yoga_name": "Easarapha Yoga", "planet1": "Mars", "planet2": "Saturn", "description": "Indicates obstacles that will eventually resolve."},
]

SAMPLE_CURRENT_VDASHA_ALL = {
    "major": {"planet": "Mercury", "start": "16-8-2012", "end": "16-8-2029"},
    "sub": {"planet": "Saturn", "start": "25-4-2025", "end": "4-1-2028"},
    "sub_sub": {"planet": "Jupiter", "start": "10-3-2026", "end": "22-8-2026"},
    "sub_sub_sub": {"planet": "Mars", "start": "1-5-2026", "end": "19-5-2026"},
    "sub_sub_sub_sub": {"planet": "Venus", "start": "8-5-2026", "end": "11-5-2026"},
}

SAMPLE_SUB_VDASHA = [
    {"planet": "Saturn", "start": "25-4-2025 08:15", "end": "4-1-2028 20:45"},
    {"planet": "Mercury", "start": "4-1-2028 20:45", "end": "12-6-2030 14:30"},
    {"planet": "Ketu", "start": "12-6-2030 14:30", "end": "1-11-2031 08:15"},
    {"planet": "Venus", "start": "1-11-2031 08:15", "end": "1-9-2034 20:45"},
]

SAMPLE_KP_PLANETS = [
    {"planet_name": "Sun", "sign": "Cancer", "sign_lord": "Moon", "star_lord": "Mercury", "sub_lord": "Venus", "degree": 118.92},
    {"planet_name": "Moon", "sign": "Aquarius", "sign_lord": "Saturn", "star_lord": "Jupiter", "sub_lord": "Mars", "degree": 325.18},
    {"planet_name": "Mars", "sign": "Taurus", "sign_lord": "Venus", "star_lord": "Mars", "sub_lord": "Rahu", "degree": 56.33},
]

SAMPLE_KP_HOUSE_CUSPS = [
    {"house": 1, "sign": "Scorpio", "degree": 236.45, "sign_lord": "Mars", "star_lord": "Mercury", "sub_lord": "Saturn"},
    {"house": 2, "sign": "Sagittarius", "degree": 265.12, "sign_lord": "Jupiter", "star_lord": "Venus", "sub_lord": "Moon"},
]

SAMPLE_KP_HOUSE_SIGNIFICATOR = [
    {"house_id": 1, "significators": ["Mars", "Saturn", "Ketu"]},
    {"house_id": 2, "significators": ["Jupiter", "Mercury"]},
    {"house_id": 3, "significators": ["Saturn", "Rahu"]},
    {"house_id": 4, "significators": ["Moon", "Saturn"]},
    {"house_id": 7, "significators": ["Venus", "Mars"]},
    {"house_id": 10, "significators": ["Mercury", "Sun"]},
]

SAMPLE_KP_PLANET_SIGNIFICATOR = [
    {"planet_id": 0, "planet": "Sun", "significators": [9, 10, 4]},
    {"planet_id": 1, "planet": "Moon", "significators": [4, 11, 2]},
    {"planet_id": 2, "planet": "Mars", "significators": [1, 7, 6]},
    {"planet_id": 3, "planet": "Mercury", "significators": [10, 8, 1]},
    {"planet_id": 4, "planet": "Jupiter", "significators": [2, 5, 8]},
    {"planet_id": 5, "planet": "Venus", "significators": [7, 9, 12]},
    {"planet_id": 6, "planet": "Saturn", "significators": [3, 4, 11]},
]

SAMPLE_MAJOR_YOGINI = [
    {"yogini_name": "Mangala", "planet": "Moon", "start": "15-8-1990", "end": "15-8-1991", "duration": "1 Year"},
    {"yogini_name": "Pingala", "planet": "Sun", "start": "15-8-1991", "end": "15-8-1993", "duration": "2 Years"},
    {"yogini_name": "Dhanya", "planet": "Jupiter", "start": "15-8-1993", "end": "15-8-1996", "duration": "3 Years"},
    {"yogini_name": "Bhramari", "planet": "Mars", "start": "15-8-1996", "end": "15-8-2000", "duration": "4 Years"},
    {"yogini_name": "Bhadrika", "planet": "Mercury", "start": "15-8-2000", "end": "15-8-2005", "duration": "5 Years"},
    {"yogini_name": "Ulka", "planet": "Saturn", "start": "15-8-2005", "end": "15-8-2011", "duration": "6 Years"},
    {"yogini_name": "Siddha", "planet": "Venus", "start": "15-8-2011", "end": "15-8-2018", "duration": "7 Years"},
    {"yogini_name": "Sankata", "planet": "Rahu", "start": "15-8-2018", "end": "15-8-2026", "duration": "8 Years"},
]

SAMPLE_CURRENT_YOGINI = {
    "yogini_name": "Sankata",
    "planet": "Rahu",
    "start": "15-8-2018",
    "end": "15-8-2026",
    "duration": "8 Years",
}

SAMPLE_SUB_YOGINI = [
    {"yogini_name": "Mangala", "planet": "Moon", "start": "15-8-2025", "end": "15-11-2025"},
    {"yogini_name": "Pingala", "planet": "Sun", "start": "15-11-2025", "end": "15-5-2026"},
    {"yogini_name": "Dhanya", "planet": "Jupiter", "start": "15-5-2026", "end": "15-8-2026"},
]

SAMPLE_CURRENT_CHARDASHA = {
    "sign": "Capricorn",
    "sign_id": 10,
    "start": "15-8-2020",
    "end": "15-8-2029",
    "duration": "9 Years",
}

SAMPLE_MAJOR_CHARDASHA = [
    {"sign": "Scorpio", "sign_id": 8, "start": "15-8-1990", "end": "15-8-1998", "duration": "8 Years"},
    {"sign": "Sagittarius", "sign_id": 9, "start": "15-8-1998", "end": "15-8-2005", "duration": "7 Years"},
    {"sign": "Capricorn", "sign_id": 10, "start": "15-8-2005", "end": "15-8-2014", "duration": "9 Years"},
    {"sign": "Aquarius", "sign_id": 11, "start": "15-8-2014", "end": "15-8-2020", "duration": "6 Years"},
    {"sign": "Pisces", "sign_id": 12, "start": "15-8-2020", "end": "15-8-2029", "duration": "9 Years"},
]

SAMPLE_SUB_CHARDASHA = [
    {"sign": "Pisces", "start": "15-8-2026", "end": "15-2-2027"},
    {"sign": "Aries", "start": "15-2-2027", "end": "15-8-2027"},
    {"sign": "Taurus", "start": "15-8-2027", "end": "15-2-2028"},
]

SAMPLE_NUMERO_TABLE = {
    "destiny_number": 6,
    "radical_number": 6,
    "name_number": 3,
    "evil_num": "8, 4",
    "fav_color": "Blue, Pink",
    "fav_day": "Friday",
    "fav_god": "Venus",
    "fav_mantra": "Om Shukraye Namah",
    "fav_metal": "Silver",
    "fav_stone": "Diamond",
    "fav_substone": "Opal",
    "friendly_num": "1, 3, 9",
    "neutral_num": "2, 5, 7",
}

SAMPLE_NUMERO_REPORT = {
    "name": "Rahul Sharma",
    "destiny_number": 6,
    "report": "Destiny number 6 indicates a life path centered on responsibility, love, and domestic harmony. The native is nurturing and artistic.",
}

SAMPLE_NUMERO_FAV_TIME = {
    "fav_time": "Evening hours between 5 PM - 7 PM",
    "fav_dates": "6, 15, 24",
    "fav_years": "2026, 2035, 2044",
}

SAMPLE_NUMERO_PLACE_VASTU = {
    "direction": "South-East",
    "vastu_tips": "Keep the south-east corner clean and well-lit. Place a Venus yantra here for prosperity.",
}

SAMPLE_NUMERO_FASTS = {
    "fasting_day": "Friday",
    "fasting_deity": "Goddess Lakshmi",
    "fasting_benefit": "Enhances love, harmony, and financial stability.",
}

SAMPLE_NUMERO_FAV_LORD = {
    "lord_name": "Goddess Lakshmi",
    "planet": "Venus",
    "benefit": "Worshipping Goddess Lakshmi brings prosperity and harmonious relationships.",
}

SAMPLE_NUMERO_FAV_MANTRA = {
    "mantra": "Om Shukraye Namah",
    "count": 108,
    "benefit": "Chanting this mantra 108 times strengthens Venus and brings artistic talents.",
}

SAMPLE_NUMERO_DAILY = {
    "date": "2026-05-12",
    "prediction": "Today is favorable for creative pursuits and financial decisions. Avoid conflicts with loved ones.",
    "lucky_number": 6,
    "lucky_color": "White",
}

SAMPLE_LALKITAB_HOROSCOPE = {
    "ascendant": "Scorpio",
    "lalkitab_chart": {
        "house_1": "Mars",
        "house_2": "Jupiter",
        "house_3": "Saturn, Rahu",
        "house_4": "Moon",
        "house_7": "Mars",
        "house_9": "Sun, Venus, Ketu",
        "house_10": "Mercury",
    },
}

SAMPLE_LALKITAB_PLANETS = [
    {"planet": "Sun", "house": 9, "status": "Exalted", "effect": "Benefic"},
    {"planet": "Moon", "house": 4, "status": "Own Sign", "effect": "Benefic"},
    {"planet": "Mars", "house": 7, "status": "Neutral", "effect": "Malefic"},
    {"planet": "Mercury", "house": 10, "status": "Friendly", "effect": "Benefic"},
    {"planet": "Jupiter", "house": 8, "status": "Debilitated", "effect": "Malefic"},
    {"planet": "Venus", "house": 9, "status": "Neutral", "effect": "Benefic"},
    {"planet": "Saturn", "house": 3, "status": "Own Sign", "effect": "Benefic"},
    {"planet": "Rahu", "house": 3, "status": "Neutral", "effect": "Neutral"},
    {"planet": "Ketu", "house": 9, "status": "Neutral", "effect": "Neutral"},
]

SAMPLE_LALKITAB_HOUSES = [
    {"house": 1, "sign": "Scorpio", "planets": ["Ascendant"], "effect": "Strong willpower"},
    {"house": 4, "sign": "Aquarius", "planets": ["Moon"], "effect": "Emotional home life"},
    {"house": 7, "sign": "Taurus", "planets": ["Mars"], "effect": "Dynamic partnerships"},
    {"house": 9, "sign": "Cancer", "planets": ["Sun", "Venus", "Ketu"], "effect": "Spiritual fortune"},
    {"house": 10, "sign": "Leo", "planets": ["Mercury"], "effect": "Career communication"},
]

SAMPLE_LALKITAB_DEBTS = [
    {"debt_type": "Self Debt", "planet": "Sun", "house": 9, "is_present": False, "description": "No self debt present."},
    {"debt_type": "Mother Debt", "planet": "Moon", "house": 4, "is_present": False, "description": "No maternal debt."},
    {"debt_type": "Relative Debt", "planet": "Mercury", "house": 10, "is_present": True, "description": "Relative debt is present due to Mercury's placement."},
]

SAMPLE_LALKITAB_REMEDIES = {
    "Sun": {"remedy": "Keep water in a red glass in sunlight and drink it.", "duration": "43 days"},
    "Moon": {"remedy": "Keep a silver square piece with you.", "duration": "Lifelong"},
    "Mars": {"remedy": "Feed sweet chapati to dogs.", "duration": "43 days"},
    "Mercury": {"remedy": "Donate green moong dal on Wednesday.", "duration": "Ongoing"},
    "Jupiter": {"remedy": "Apply saffron tilak on forehead.", "duration": "43 days"},
    "Venus": {"remedy": "Donate cow ghee to a temple.", "duration": "Ongoing"},
    "Saturn": {"remedy": "Feed crows with cooked rice.", "duration": "43 days"},
    "Rahu": {"remedy": "Keep a silver ball with you.", "duration": "Lifelong"},
    "Ketu": {"remedy": "Donate blankets to the needy.", "duration": "Ongoing"},
}

SAMPLE_BIORHYTHM = {
    "physical": {"value": 72.5, "phase": "High", "description": "Physical energy is strong."},
    "emotional": {"value": -45.2, "phase": "Low", "description": "Emotional sensitivity is heightened."},
    "intellectual": {"value": 88.1, "phase": "Peak", "description": "Mental clarity is excellent."},
}

SAMPLE_MOON_BIORHYTHM = {
    "lunar_physical": {"value": 55.3, "phase": "Rising"},
    "lunar_emotional": {"value": -22.8, "phase": "Falling"},
    "lunar_intellectual": {"value": 91.0, "phase": "Peak"},
}

SAMPLE_KUNDLI_DATA = KundliData(
    request=SAMPLE_REQUEST,
    birth_details=SAMPLE_BIRTH_DETAILS,
    planets=SAMPLE_PLANETS,
    planets_extended=SAMPLE_PLANETS,
    houses=SAMPLE_HOUSES,
    horo_chart_d1=SAMPLE_HORO_CHART,
    natal_wheel_chart=None,
    natal_chart_svg=None,
    panchang=SAMPLE_PANCHANG,
    basic_panchang=SAMPLE_BASIC_PANCHANG,
    basic_panchang_sunrise=SAMPLE_BASIC_PANCHANG,
    advanced_panchang_sunrise=SAMPLE_BASIC_PANCHANG,
    planet_panchang=SAMPLE_PLANET_PANCHANG,
    planet_panchang_sunrise=SAMPLE_PLANET_PANCHANG,
    chaughadiya_muhurta=SAMPLE_CHAUGHADIYA,
    hora_muhurta=SAMPLE_HORA_MUHURTA,
    panchang_chart=SAMPLE_PANCHANG_CHART,
    panchang_festival=SAMPLE_PANCHANG_FESTIVAL,
    current_vdasha=SAMPLE_CURRENT_DASHA,
    major_vdasha=SAMPLE_MAJOR_VDASHA,
    kp_birth_chart=SAMPLE_KP_CHART,
    sarvashtak=SAMPLE_SARVASHTAK,
    ayanamsha_details=SAMPLE_AYANAMSHA,
    astro_details=SAMPLE_ASTRO_DETAILS,
    ghat_chakra=SAMPLE_GHAT_CHAKRA,
    bhav_madhya=SAMPLE_BHAV_MADHYA,
    planet_nature=SAMPLE_PLANET_NATURE,
    panchada_maitri=SAMPLE_PANCHADA_MAITRI,
    planet_ashtak=SAMPLE_PLANET_ASHTAK,
    horo_charts=SAMPLE_HORO_CHARTS,
    horo_chart_images=None,
    horo_chart_extended=None,
    general_ascendant_report=SAMPLE_ASCENDANT_REPORT,
    general_nakshatra_report=SAMPLE_NAKSHATRA_REPORT,
    general_house_reports=SAMPLE_HOUSE_REPORTS,
    general_rashi_reports=SAMPLE_RASHI_REPORTS,
    simple_manglik=SAMPLE_SIMPLE_MANGLIK,
    manglik=SAMPLE_MANGLIK,
    kalsarpa_details=SAMPLE_KALSARPA,
    sadhesati_current_status=SAMPLE_SADHESATI_STATUS,
    sadhesati_life_details=SAMPLE_SADHESATI_LIFE,
    pitra_dosha_report=SAMPLE_PITRA_DOSHA,
    puja_suggestion=SAMPLE_PUJA,
    basic_gem_suggestion=SAMPLE_GEMS,
    rudraksha_suggestion=SAMPLE_RUDRAKSHA,
    sadhesati_remedies=SAMPLE_SADHESATI_REMEDIES,
    daily_nakshatra_prediction=SAMPLE_DAILY_PREDICTION,
    daily_nakshatra_prediction_next=SAMPLE_DAILY_PREDICTION_NEXT,
    daily_nakshatra_prediction_previous=SAMPLE_DAILY_PREDICTION_PREV,
    varshaphal_details=SAMPLE_VARSHAPHAL_DETAILS,
    varshaphal_planets=SAMPLE_VARSHAPHAL_PLANETS,
    varshaphal_muntha=SAMPLE_VARSHAPHAL_MUNTHA,
    varshaphal_yoga=SAMPLE_VARSHAPHAL_YOGA,
    current_vdasha_all=SAMPLE_CURRENT_VDASHA_ALL,
    sub_vdasha=SAMPLE_SUB_VDASHA,
    kp_planets=SAMPLE_KP_PLANETS,
    kp_house_cusps=SAMPLE_KP_HOUSE_CUSPS,
    kp_house_significator=SAMPLE_KP_HOUSE_SIGNIFICATOR,
    kp_planet_significator=SAMPLE_KP_PLANET_SIGNIFICATOR,
    major_yogini_dasha=SAMPLE_MAJOR_YOGINI,
    current_yogini_dasha=SAMPLE_CURRENT_YOGINI,
    sub_yogini_dasha=SAMPLE_SUB_YOGINI,
    current_chardasha=SAMPLE_CURRENT_CHARDASHA,
    major_chardasha=SAMPLE_MAJOR_CHARDASHA,
    sub_chardasha=SAMPLE_SUB_CHARDASHA,
    numero_table=SAMPLE_NUMERO_TABLE,
    numero_report=SAMPLE_NUMERO_REPORT,
    numero_fav_time=SAMPLE_NUMERO_FAV_TIME,
    numero_place_vastu=SAMPLE_NUMERO_PLACE_VASTU,
    numero_fasts_report=SAMPLE_NUMERO_FASTS,
    numero_fav_lord=SAMPLE_NUMERO_FAV_LORD,
    numero_fav_mantra=SAMPLE_NUMERO_FAV_MANTRA,
    numero_prediction_daily=SAMPLE_NUMERO_DAILY,
    lalkitab_horoscope=SAMPLE_LALKITAB_HOROSCOPE,
    lalkitab_planets=SAMPLE_LALKITAB_PLANETS,
    lalkitab_houses=SAMPLE_LALKITAB_HOUSES,
    lalkitab_debts=SAMPLE_LALKITAB_DEBTS,
    lalkitab_remedies=SAMPLE_LALKITAB_REMEDIES,
    biorhythm=SAMPLE_BIORHYTHM,
    moon_biorhythm=SAMPLE_MOON_BIORHYTHM,
)

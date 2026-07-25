from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import pathlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import aiosqlite
from anthropic import AsyncAnthropic

from config import settings
from sections import planet_to_en

if TYPE_CHECKING:
    from models import KundliData

logger = logging.getLogger(__name__)

DB_PATH = (
    pathlib.Path(settings.narrative_cache_path)
    if settings.narrative_cache_path
    else pathlib.Path(__file__).parent / "narrative_cache.db"
)
# Flagship narratives now run on Haiku 4.5 (cost cut). Sonnet is no longer the default,
# so the use_haiku_for_* switches below resolve to Haiku on both branches.
NARRATIVE_MODEL = "claude-haiku-4-5-20251001"
TRANSLATION_MODEL = "claude-haiku-4-5-20251001"
# Formulaic narrative batches (planets, numerology) route here when the
# use_haiku_for_simple_narratives kill-switch is on. Same Haiku model as translation.
SIMPLE_NARRATIVE_MODEL = "claude-haiku-4-5-20251001"
MODEL = NARRATIVE_MODEL
MAX_CONCURRENT = settings.narrative_concurrency
CALL_TIMEOUT = 30.0

# USD per token. Cache reads cost 0.1x input; cache writes cost 1.25x input.
MODEL_PRICING = {
    "claude-sonnet-4-20250514":  {"in": 3 / 1e6, "out": 15 / 1e6, "cache_read": 0.30 / 1e6, "cache_write": 3.75 / 1e6},
    "claude-haiku-4-5-20251001": {"in": 1 / 1e6, "out": 5 / 1e6,  "cache_read": 0.10 / 1e6, "cache_write": 1.25 / 1e6},
}


def _log_usage(model: str, usage: Any, label: str, sink: list[float] | None = None) -> float:
    """Log per-call token usage + estimated USD cost; append cost to sink if given."""
    p = MODEL_PRICING.get(model, {})
    in_tok = getattr(usage, "input_tokens", 0) or 0
    out_tok = getattr(usage, "output_tokens", 0) or 0
    cache_r = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_w = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cost = (
        in_tok * p.get("in", 0)
        + out_tok * p.get("out", 0)
        + cache_r * p.get("cache_read", 0)
        + cache_w * p.get("cache_write", 0)
    )
    logger.info(
        "COST %s model=%s in=%d out=%d cache_r=%d cache_w=%d => $%.4f",
        label, model, in_tok, out_tok, cache_r, cache_w, cost,
    )
    if sink is not None:
        sink.append(cost)
    return cost

_db_lock = asyncio.Lock()
_db_ready = False

_SYSTEM_PROMPT_EN = """\
You are an experienced Vedic astrologer writing for an urban Indian audience aged 22-45.
Write in warm, conversational English. Keep Sanskrit terms as-is (Mahadasha, Lagna, Nakshatra).

Structure: exactly 2 short paragraphs, 70-95 words total.
Paragraph 1: What this placement/period/yoga means in everyday-life terms with a vivid modern metaphor.
Paragraph 2: How it shows up in career, relationships, money, or health (pick what is most relevant), plus one watch-out or balance lesson, ending on a warm note.

Tone: warm, relatable, like a best friend who knows astrology. Never preachy, never doom-laden.
- Saturn challenges become "growth invitations".
- Manglik becomes "your inner fire".
- Sade Sati becomes "a 7.5-year masterclass".

FORBIDDEN: predictions of death, exact dates of bad events, anything that could scare a vulnerable reader.
You MUST reference the actual astrological data provided (sign, house, planet, nakshatra, dates). Never invent data.
End every response with a complete sentence ending in a period. If running out of space, wrap up the current thought cleanly rather than starting a new one.
Output ONLY the narrative text. No headings, no markdown, no bullet points, no asterisks."""

_SYSTEM_PROMPT_HI = """\
आप एक अनुभवी वैदिक ज्योतिषी हैं जो शहरी भारतीय पाठकों (आयु 22-45) के लिए लिखते हैं।
पूर्ण शुद्ध हिंदी में लिखें। कोई भी अंग्रेज़ी शब्द न मिलाएं। ज्योतिषीय शब्द संस्कृत/हिंदी में रखें
(महादशा, लग्न, नक्षत्र, राशि, भाव, ग्रह)।

संरचना: ठीक 2 छोटे अनुच्छेद, कुल 60-85 शब्द।
अनुच्छेद 1: इस स्थिति/काल/योग का दैनिक जीवन में क्या अर्थ है — एक सजीव आधुनिक उपमा के साथ।
अनुच्छेद 2: करियर, रिश्तों, धन या स्वास्थ्य में यह कैसे प्रकट होता है (जो सबसे प्रासंगिक हो), साथ ही एक सावधानी या संतुलन का सबक, गर्मजोशी से समाप्त करें।

स्वर: गर्मजोशी भरा, मित्रवत, जैसे कोई करीबी मित्र जो ज्योतिष जानता हो। कभी उपदेशात्मक नहीं, कभी भयभीत करने वाला नहीं।
- शनि की चुनौतियों को "विकास का निमंत्रण" कहें।
- मांगलिक को "आपकी आंतरिक अग्नि" कहें।
- साढ़ेसाती को "साढ़े सात वर्ष की गहन शिक्षा" कहें।

वर्जित: मृत्यु की भविष्यवाणी, बुरी घटनाओं की सटीक तिथियां, कोई भी बात जो पाठक को डराए।
आपको दिए गए वास्तविक ज्योतिषीय आंकड़ों का उपयोग करना अनिवार्य है (राशि, भाव, ग्रह, नक्षत्र, तिथियां)। कोई आंकड़ा गढ़ें नहीं।
प्रत्येक उत्तर को पूर्ण वाक्य के साथ समाप्त करें जो '।' पर समाप्त हो। यदि स्थान कम हो रहा हो तो वर्तमान विचार को साफ़-सुथरे ढंग से समाप्त करें, नया विचार शुरू न करें।
केवल विवरण लिखें। कोई शीर्षक नहीं, कोई मार्कडाउन नहीं, कोई बुलेट पॉइंट नहीं, कोई तारांकन नहीं।"""

_SYSTEM_PROMPT_MAHADASHA_EN = """\
You are an experienced Vedic astrologer writing for an urban Indian audience aged 22-45.

For the given Mahadasha period, generate a structured response in VALID JSON format:
{
  "experience": ["bullet 1", "bullet 2", "bullet 3"],
  "avoid": ["bullet 1", "bullet 2", "bullet 3"]
}

"experience": exactly 3 one-sentence bullets about what the native will experience during this period.
"avoid": exactly 3 one-sentence bullets about what the native should avoid during this period.

Each bullet: 10-14 words, warm conversational tone. Reference the actual planet, sign, and house.
Tone: warm, relatable, like a best friend who knows astrology. Never preachy, never doom-laden.
Saturn challenges = "growth invitations". Rahu = "desire amplifier". Ketu = "spiritual teacher".
FORBIDDEN: predictions of death, exact dates of bad events, anything that could scare a reader.
Output ONLY the JSON. No markdown fences, no explanation."""

_SYSTEM_PROMPT_MAHADASHA_HI = """\
आप एक अनुभवी वैदिक ज्योतिषी हैं जो शहरी भारतीय पाठकों (आयु 22-45) के लिए लिखते हैं।
पूर्ण शुद्ध हिंदी में लिखें। कोई भी अंग्रेज़ी शब्द न मिलाएं।

दी गई महादशा के लिए इस JSON प्रारूप में उत्तर दें:
{
  "experience": ["बुलेट 1", "बुलेट 2", "बुलेट 3"],
  "avoid": ["बुलेट 1", "बुलेट 2", "बुलेट 3"]
}

"experience": ठीक 3 एक-वाक्य बुलेट — इस काल में जातक क्या अनुभव करेगा।
"avoid": ठीक 3 एक-वाक्य बुलेट — इस काल में जातक को किन बातों से बचना चाहिए।

प्रत्येक बुलेट: 10-14 शब्द, गर्मजोशी भरा स्वर। वास्तविक ग्रह, राशि और भाव का उल्लेख करें।
शनि की चुनौतियां = "विकास का निमंत्रण"। राहु = "इच्छा प्रवर्धक"। केतु = "आध्यात्मिक गुरु"।
वर्जित: मृत्यु की भविष्यवाणी, बुरी घटनाओं की तिथियां, भयभीत करने वाली बातें।
केवल JSON लिखें। कोई मार्कडाउन नहीं, कोई व्याख्या नहीं।"""

_SYSTEM_PROMPT_VARSHAPHAL_EN = """\
You are an experienced Vedic astrologer writing an annual forecast (Varshaphal) for an urban Indian audience aged 22-45.

For the given Varshaphal (annual/Tajik) chart, generate a structured response in VALID JSON format:
{
  "overall": "2-3 sentences on the year's overall theme from the Varsha Lagna and Year Lord (Varshesh).",
  "career": "2-4 sentences on career, work, and professional growth this year.",
  "health": "2-4 sentences on health, energy, and wellbeing this year.",
  "wealth": "2-4 sentences on money, finances, and material gains this year.",
  "family": "2-4 sentences on family, home, and relationships this year."
}

Ground every point in the actual chart data provided (Varsha Lagna, Muntha, Varshesh, yogas). Do not invent data.
Tone: warm, encouraging, grounded — like a trusted friend who knows astrology. Never preachy, never doom-laden.
Saturn challenges = "growth invitations". FORBIDDEN: predictions of death, exact dates of bad events, anything that could scare a reader.
Output ONLY the JSON. No markdown fences, no explanation."""

_SYSTEM_PROMPT_VARSHAPHAL_HI = """\
आप एक अनुभवी वैदिक ज्योतिषी हैं जो शहरी भारतीय पाठकों (आयु 22-45) के लिए वार्षिक भविष्यवाणी (वर्षफल) लिखते हैं।
पूर्ण शुद्ध हिंदी में लिखें। कोई भी अंग्रेज़ी शब्द न मिलाएं।

दिए गए वर्षफल (वार्षिक/ताजिक) चक्र के लिए इस JSON प्रारूप में उत्तर दें:
{
  "overall": "वर्ष लग्न और वर्षेश से इस वर्ष का समग्र स्वरूप — 2-3 वाक्य।",
  "career": "इस वर्ष करियर, कार्य और व्यावसायिक प्रगति — 2-4 वाक्य।",
  "health": "इस वर्ष स्वास्थ्य, ऊर्जा और कल्याण — 2-4 वाक्य।",
  "wealth": "इस वर्ष धन, वित्त और भौतिक लाभ — 2-4 वाक्य।",
  "family": "इस वर्ष परिवार, गृह और रिश्ते — 2-4 वाक्य।"
}

प्रत्येक बात को दिए गए वास्तविक चक्र आंकड़ों (वर्ष लग्न, मुंथा, वर्षेश, योग) पर आधारित रखें। कोई आंकड़ा न गढ़ें।
स्वर: गर्मजोशी भरा, प्रोत्साहक, यथार्थपरक। कभी उपदेशात्मक नहीं, कभी भयभीत करने वाला नहीं।
शनि की चुनौतियां = "विकास का निमंत्रण"। वर्जित: मृत्यु की भविष्यवाणी, बुरी घटनाओं की तिथियां, भयभीत करने वाली बातें।
JSON कुंजियां (overall, career, health, wealth, family) अंग्रेज़ी में रखें; मान हिंदी में लिखें।
केवल JSON लिखें। कोई मार्कडाउन नहीं, कोई व्याख्या नहीं।"""


def _salvage_truncated_json(raw: str) -> str:
    """Best-effort repair of JSON truncated by max_tokens."""
    last_complete = max(
        raw.rfind('",'),
        raw.rfind('"}'),
    )
    if last_complete == -1:
        return "{}"
    salvaged = raw[: last_complete + 1]
    if not salvaged.rstrip().endswith("}"):
        salvaged = salvaged.rstrip().rstrip(",") + "}"
    return salvaged


_REMEDY_CACHE_V2 = frozenset({
    "rudraksha_guidance", "rudraksha_personal", "gemstone_benefit",
    "ishta_devata", "mantra_guidance", "yantra_guidance", "daan_guidance",
})

# Bump when a section's output SHAPE changes so stale cache entries are not reused.
# varshaphal switched from a plain-text paragraph to structured category JSON.
_CACHE_V2 = _REMEDY_CACHE_V2 | frozenset({"varshaphal"})


def _cache_key(section_type: str, data: dict, lang: str) -> str:
    version_suffix = ":v2" if section_type in _CACHE_V2 else ""
    raw = f"{section_type}{version_suffix}:{lang}:{json.dumps(data, sort_keys=True, default=str)}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def _ensure_db() -> None:
    global _db_ready
    if _db_ready:
        return
    async with _db_lock:
        if _db_ready:
            return
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute(
                "CREATE TABLE IF NOT EXISTS cache "
                "(key TEXT PRIMARY KEY, narrative TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            await db.commit()
        _db_ready = True


async def _get_cached(key: str) -> str | None:
    await _ensure_db()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT narrative FROM cache WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def _set_cached(key: str, narrative: str) -> None:
    await _ensure_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO cache (key, narrative, created_at) VALUES (?, ?, ?)",
            (key, narrative, datetime.now(timezone.utc).isoformat()),
        )
        await db.commit()


def _build_user_prompt(section_type: str, data: dict, lang: str) -> str:
    if section_type == "planet_placement":
        return (
            f"Planet: {data['name']}\n"
            f"Sign: {data['sign']} (Lord: {data['signLord']})\n"
            f"House: {data['house']}\n"
            f"Nakshatra: {data['nakshatra']} (Lord: {data['nakshatraLord']}, Pada: {data['pada']})\n"
            f"Degree: {data['degree']}°\n"
            f"Retrograde: {'Yes' if data.get('isRetro') == 'true' else 'No'}\n\n"
            f"Write a narrative about what this planet's placement means for the native's life."
        )
    if section_type == "mahadasha_period":
        return (
            f"Current Mahadasha: {data['major_planet']}\n"
            f"Mahadasha planet's sign: {data.get('sign', 'unknown')}, House: {data.get('house', 'unknown')}\n"
            f"Period: {data['start']} to {data['end']}\n"
            f"Current Antardasha: {data.get('minor_planet', 'unknown')}\n\n"
            f"Write a narrative about the current life period (Mahadasha) for the native."
        )
    if section_type == "raj_yoga":
        return (
            f"Yoga: {data['name']}\n"
            f"Planets involved: {data['planets']}\n"
            f"House: {data['house']}\n"
            f"Effect: {data['effect']}\n"
            f"Classical description: {data['description']}\n\n"
            f"Write a personalized narrative about what this yoga means for the native's life."
        )
    if section_type == "lagna_pillar":
        return (
            f"Lagna (Ascendant): {data['sign']}\n"
            f"Lagna Lord: {data['lord']}\n"
            f"Lagna Nakshatra: {data['nakshatra']} (Lord: {data['nakshatraLord']})\n"
            f"Lagna Degree: {data['degree']}°\n\n"
            f"Write a narrative about what this Lagna means for the native's core personality, "
            f"public persona, and life approach. This is the first of the Three Pillars of Self."
        )
    if section_type == "moon_rashi_pillar":
        return (
            f"Moon Rashi (Moon Sign): {data['sign']}\n"
            f"Moon Sign Lord: {data['signLord']}\n"
            f"Moon House: {data['house']}\n"
            f"Moon Nakshatra: {data['nakshatra']}\n\n"
            f"Write a narrative about what this Moon sign means for the native's emotional world, "
            f"inner nature, and intuitive patterns. This is the second of the Three Pillars of Self."
        )
    if section_type == "nakshatra_pillar":
        return (
            f"Janma Nakshatra: {data['nakshatra']}\n"
            f"Nakshatra Lord: {data['lord']}\n"
            f"Nakshatra Pada: {data['pada']}\n"
            f"Nakshatra Sign: {data['sign']}\n\n"
            f"Write a narrative about what this birth nakshatra means for the native's soul blueprint, "
            f"destiny patterns, and spiritual inclination. This is the third of the Three Pillars of Self."
        )
    if section_type == "sade_sati_overview":
        phases = data.get("phases", [])
        timeline = "; ".join(
            f"{p['type']} → Saturn in {p['saturn_sign']} ({p['date']})" for p in phases[:24]
        )
        return (
            f"Moon Sign: {data.get('moon_sign', '')}\n"
            f"Currently undergoing Sade Sati: {data.get('is_active', False)}\n"
            f"Transition timeline across life: {timeline}\n\n"
            "Write ONE concise overview (2 short paragraphs, ~110-140 words total) of the person's overall "
            "Sade Sati journey — explain the Rising → Peak → Setting arc in plain terms, what these periods "
            "bring, and end on a reassuring, growth-framed note. Do NOT list individual dates or enumerate "
            "every phase; summarize the pattern warmly."
        )
    if section_type == "raj_yoga_celebration":
        return (
            f"Yoga: {data['name']}\n"
            f"Planets involved: {data['planets']}\n"
            f"House: {data['house']}\n"
            f"Effect: {data['effect']}\n"
            f"Classical description: {data['description']}\n\n"
            f"Write a celebratory narrative (about 120 words) about what this Raj Yoga "
            f"means for the native's life. Emphasize the gift of having this yoga. "
            f"Be specific about which life areas it blesses. "
            f"End with one actionable tip on how to activate this yoga's potential."
        )
    if section_type == "mahadasha_journey":
        return (
            f"Mahadasha Planet: {data['planet']}\n"
            f"Planet's Sign: {data['sign']}\n"
            f"Planet's House: {data['house']}\n"
            f"Planet's Nakshatra: {data['nakshatra']}\n"
            f"Period: {data['start']} to {data['end']}\n"
            f"Is Retrograde: {data.get('isRetro', 'false')}\n\n"
            f"Generate the structured experience and avoid bullets for this Mahadasha."
        )
    if section_type == "numerology_personality":
        return (
            f"Number Type: {data['number_type']}\n"
            f"Number Value: {data['value']}\n"
            f"Native's Name: {data['name']}\n"
            f"Birth Day: {data['day']}, Month: {data['month']}, Year: {data['year']}\n\n"
            f"Write a narrative about this numerology number's meaning for the native's personality. "
            f"Include: (1) personality traits in 2-3 sentences, (2) one career suggestion area, "
            f"(3) one life challenge to be aware of. Keep total to about 100-120 words."
        )
    if section_type == "rudraksha_guidance":
        mukhi_str = ", ".join(str(m) for m in data.get("mukhi_list", []))
        return (
            f"Recommended Rudraksha Mukhi: {mukhi_str}\n\n"
            f"Write a comprehensive guide (about 150-200 words) covering:\n"
            f"1. How to wear Rudraksha — the Shukla Paksha Monday ritual, ghee soak purification, "
            f"'Om Namah Shivaya' 108 jaap activation, gold/silver/red-thread stringing options, "
            f"neckline placement near heart, keeping under clothes.\n"
            f"2. How to spot a fake — surface texture, water test, milk test, lens inspection, X-ray.\n"
            f"Write as flowing prose, not bullet points."
        )
    if section_type == "rudraksha_personal":
        mukhi_str = ", ".join(str(m) for m in data.get("mukhi_list", []))
        return (
            f"Recommended Rudraksha: {mukhi_str} Mukhi\n"
            f"Planets: {data.get('planets', '')}\n"
            f"Nakshatra: {data.get('nakshatra', '')}\n\n"
            f"Write a personalized narrative (about 120 words) explaining why these specific "
            f"Rudraksha types are recommended for this native based on their planetary positions. "
            f"Be warm and specific about the benefits they will experience."
        )
    if section_type == "gemstone_benefit":
        return (
            f"Gemstone: {data['gem_name']}\n"
            f"Planet: {data['planet']}\n"
            f"Stone Type: {data['type']}\n"
            f"Lagna: {data.get('lagna', 'unknown')}\n\n"
            f"Write a benefit narrative (about 100 words) for this gemstone covering four areas: "
            f"career impact, health benefits, relationship influence, and financial effect. "
            f"Be specific to the planet's energy and the native's chart context."
        )
    if section_type == "ishta_devata":
        return (
            f"Ishta Devata: {data['deity']}\n"
            f"12th House Lord: {data['twelfth_lord']} in {data['twelfth_sign']}\n"
            f"Moon Sign: {data.get('moon_sign', 'unknown')}\n\n"
            f"Write a full devotional narrative (about 200 words) covering:\n"
            f"1. Who is this deity and what they represent\n"
            f"2. Why this deity is the native's Ishta Devata based on their chart\n"
            f"3. Suggested daily practice (simple, practical)\n"
            f"4. End with a sacred shloka or invocation for this deity\n"
            f"Write warmly, as if guiding a friend to their spiritual anchor."
        )
    if section_type == "mantra_guidance":
        weak = ", ".join(data.get("weak_planets", []))
        return (
            f"Weak/Afflicted Planets: {weak or 'None identified'}\n"
            f"Ishta Devata: {data.get('ishta_devata', 'unknown')}\n\n"
            f"Write a brief narrative (about 100 words) introducing mantra practice for this native. "
            f"Mention which planet mantras they should prioritize based on their weak planets, "
            f"and how daily chanting creates gradual transformation. Be warm and encouraging."
        )
    if section_type == "yantra_guidance":
        return (
            f"Recommended Yantra: {data['yantra']}\n"
            f"For Planet: {data['planet']}\n"
            f"Planet Dignity: {data['dignity']}\n"
            f"Planet House: {data['house']}\n"
            f"Planet Sign: {data.get('sign', 'unknown')}\n\n"
            f"Write a narrative (about 120 words) explaining why this yantra is recommended "
            f"for the native, how it will help balance the planet's energy, and the spiritual "
            f"significance of yantra worship. Be warm and practical."
        )
    if section_type == "daan_guidance":
        planets_str = ", ".join(
            f"{p['name']} ({p['dignity']})" for p in data.get("weak_planets", [])
        )
        return (
            f"Weak/Afflicted Planets: {planets_str or 'None'}\n\n"
            f"Write a narrative (about 120 words) about the power of Daan (sacred donations) "
            f"in Vedic astrology. Explain how donating specific items on specific days helps "
            f"balance planetary energy. Mention the weak planets and how targeted donations "
            f"can bring relief. End with an encouraging note about consistency. "
            f"Be warm, never guilt-inducing."
        )
    if section_type == "outer_planet":
        return (
            f"Planet: {data['name']} (associated with Vedic deity: {data['deity']})\n"
            f"Sign: {data['sign']} (Lord: {data['signLord']})\n"
            f"House: {data['house']}\n"
            f"Nakshatra: {data['nakshatra']}\n"
            f"Retrograde: {'Yes' if data.get('isRetro') == 'true' else 'No'}\n\n"
            f"Write a narrative about this outer planet's placement. Start by connecting "
            f"its energy to its Vedic deity association ({data['deity']}). Then explain how "
            f"this placement affects the native's generational patterns, subconscious drives, "
            f"and life transformations. These are slow-moving planets — focus on deep, "
            f"long-term themes rather than day-to-day events."
        )
    if section_type == "marriage_timing":
        return (
            f"7th House Sign: {data['seventh_sign']} (Lord: {data['seventh_lord']})\n"
            f"7th Lord Placement: House {data.get('seventh_lord_house', '?')} in {data.get('seventh_lord_sign', '?')}\n"
            f"Venus: House {data.get('venus_house', '?')} in {data.get('venus_sign', '?')}\n"
            f"Planets in 7th House: {data.get('planets_in_7', 'None')}\n\n"
            f"Write a narrative about the native's marriage prospects and timing indicators. "
            f"Cover: what kind of partner and married life the chart suggests, "
            f"which Mahadasha periods are most favorable for marriage, "
            f"and one practical relationship insight. Keep it warm and hopeful."
        )
    if section_type == "varshaphal":
        return (
            f"Varshaphal (Annual / Tajik) Chart for year {data.get('year', '?')}\n"
            f"Annual Ascendant (Varsha Lagna): {data.get('ascendant', '?')}\n"
            f"Muntha: {data.get('muntha_sign', '?')} in House {data.get('muntha_house', '?')} "
            f"(Lord: {data.get('muntha_lord', '?')})\n"
            f"Year Lord (Varshesh): {data.get('varshesh', '?')} — Strength: {data.get('varshesha_strength', '?')}\n"
            f"Key Yogas: {data.get('yogas', 'None')}"
        )
    if section_type == "career_path":
        return (
            f"10th House Sign: {data['tenth_sign']} (Lord: {data['tenth_lord']})\n"
            f"10th Lord Placement: House {data.get('tenth_lord_house', '?')}\n"
            f"Sun: House {data.get('sun_house', '?')} in {data.get('sun_sign', '?')}\n"
            f"Saturn: House {data.get('saturn_house', '?')} in {data.get('saturn_sign', '?')}\n"
            f"Amatyakaraka: {data.get('amatyakaraka', 'Not computed')}\n\n"
            f"Write a narrative about the native's career path and professional destiny. "
            f"Cover: natural career strengths from the 10th house, "
            f"how Sun and Saturn shape authority and discipline in work, "
            f"and one specific career direction the chart supports."
        )
    if section_type == "material_comforts":
        return (
            f"4th House Sign: {data['fourth_sign']} (Lord: {data['fourth_lord']})\n"
            f"4th Lord Placement: House {data.get('fourth_lord_house', '?')}\n"
            f"Venus: House {data.get('venus_house', '?')} in {data.get('venus_sign', '?')}\n"
            f"Mars: House {data.get('mars_house', '?')} in {data.get('mars_sign', '?')}\n\n"
            f"Write a warm narrative about the native's material comforts — home, property, "
            f"land, and vehicles. Cover: what the 4th house and its lord suggest about domestic "
            f"happiness and owning a home, how Venus shapes comfort, luxury and vehicles, "
            f"what Mars indicates for land/property, and one practical, encouraging focus. "
            f"Keep it grounded and hopeful — avoid fear or rigid predictions."
        )
    if section_type == "love_marriage":
        return (
            f"5th House Sign: {data['fifth_sign']} (Lord: {data['fifth_lord']})\n"
            f"7th House Sign: {data['seventh_sign']} (Lord: {data['seventh_lord']})\n"
            f"Venus: House {data.get('venus_house', '?')} in {data.get('venus_sign', '?')}\n"
            f"Darakaraka: {data.get('darakaraka', 'Not computed')}\n\n"
            f"Write a narrative about the native's love life and romantic nature. "
            f"Cover: how the 5th house shapes romantic attraction, "
            f"what the 7th house reveals about the ideal partner, "
            f"and how Venus influences emotional expression in love."
        )
    if section_type == "spiritual_potential":
        return (
            f"9th House Sign: {data['ninth_sign']} (Lord: {data['ninth_lord']})\n"
            f"12th House Sign: {data['twelfth_sign']} (Lord: {data['twelfth_lord']})\n"
            f"Jupiter: House {data.get('jupiter_house', '?')} in {data.get('jupiter_sign', '?')}\n"
            f"Ketu: House {data.get('ketu_house', '?')} in {data.get('ketu_sign', '?')}\n"
            f"Atmakaraka: {data.get('atmakaraka', 'Not computed')}\n\n"
            f"Write a narrative about the native's spiritual potential and dharmic path. "
            f"Cover: what the 9th and 12th houses reveal about spiritual inclination, "
            f"how Jupiter and Ketu guide the soul's journey, "
            f"and one practical spiritual practice the chart supports."
        )
    if section_type == "rahu_ketu_analysis":
        return (
            f"Rahu: House {data['rahu_house']} in {data['rahu_sign']}\n"
            f"Rahu Nakshatra: {data.get('rahu_nakshatra', '?')}\n"
            f"Ketu: House {data['ketu_house']} in {data['ketu_sign']}\n"
            f"Ketu Nakshatra: {data.get('ketu_nakshatra', '?')}\n"
            f"Axis: {data.get('axis', '?')}\n\n"
            f"Write a narrative about this Rahu-Ketu axis and its karmic significance. "
            f"Cover: what past-life patterns Ketu brings, "
            f"what this-life desires Rahu amplifies, "
            f"and how to balance both poles for growth. "
            f"Keep the tone empowering — karmic lessons are growth opportunities."
        )
    return f"Section: {section_type}\nData: {json.dumps(data, default=str)}\n\nWrite a brief narrative."


async def narrate(
    section_type: str,
    data: dict,
    lang: str,
    client: AsyncAnthropic,
    semaphore: asyncio.Semaphore,
) -> str:
    key = _cache_key(section_type, data, lang)

    try:
        cached = await _get_cached(key)
        if cached:
            logger.debug("Narrative cache hit: %s", section_type)
            return cached
    except Exception:
        logger.warning("Cache read failed for %s", section_type, exc_info=True)

    if section_type == "mahadasha_journey":
        system_prompt = _SYSTEM_PROMPT_MAHADASHA_HI if lang == "hi" else _SYSTEM_PROMPT_MAHADASHA_EN
        max_tokens = 820
    else:
        system_prompt = _SYSTEM_PROMPT_HI if lang == "hi" else _SYSTEM_PROMPT_EN
        max_tokens = 560
    user_prompt = _build_user_prompt(section_type, data, lang)

    try:
        async with semaphore:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=MODEL,
                    max_tokens=max_tokens,
                    temperature=0.7,
                    system=[{
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }],
                    messages=[{"role": "user", "content": user_prompt}],
                ),
                timeout=CALL_TIMEOUT,
            )
        _log_usage(MODEL, response.usage, f"narrate:{section_type}")
        narrative = response.content[0].text.strip()

        if response.stop_reason == "max_tokens":
            logger.warning("Narrative '%s' hit max_tokens, trimming to last sentence", section_type)
            for terminator in ("।", ".", "!", "?", "\"", "}"):
                idx = narrative.rfind(terminator)
                if idx > len(narrative) * 0.5:
                    narrative = narrative[:idx + 1]
                    break

        try:
            await _set_cached(key, narrative)
        except Exception:
            logger.warning("Cache write failed for %s", section_type, exc_info=True)

        logger.info("Narrative generated: %s (%d chars)", section_type, len(narrative))
        return narrative

    except Exception:
        logger.warning("Narrative generation failed for %s", section_type, exc_info=True)
        return ""


async def _batch_narrate(
    items: dict[str, tuple[str, dict]],
    lang: str,
    client: AsyncAnthropic,
    semaphore: asyncio.Semaphore,
    use_mahadasha_prompt: bool = False,
    batch_kind: str = "generic",
    label: str = "",
    cost_sink: list[float] | None = None,
    model: str | None = None,
) -> dict[str, str]:
    if not items:
        return {}

    # Chunk oversized batches so no single API call exceeds the timeout / token budget.
    # Recursive: a 30-item batch splits into 10-item calls, each under the limit (no re-split).
    # Chunks run concurrently; a failed chunk loses only its items, not the whole batch.
    _MAX_BATCH_ITEMS = 10
    if len(items) > _MAX_BATCH_ITEMS:
        item_list = list(items.items())
        chunks = [
            dict(item_list[i:i + _MAX_BATCH_ITEMS])
            for i in range(0, len(item_list), _MAX_BATCH_ITEMS)
        ]
        logger.info(
            "Batch narrate: splitting %d items into %d chunks (kind=%s)",
            len(items), len(chunks), batch_kind,
        )
        chunk_results = await asyncio.gather(
            *(
                _batch_narrate(
                    chunk, lang, client, semaphore,
                    use_mahadasha_prompt=use_mahadasha_prompt,
                    batch_kind=batch_kind,
                    label=label,
                    cost_sink=cost_sink,
                    model=model,
                )
                for chunk in chunks
            ),
            return_exceptions=True,
        )
        merged: dict[str, str] = {}
        for i, result in enumerate(chunk_results):
            if isinstance(result, Exception):
                logger.warning("Narrative chunk %d failed (kind=%s): %s", i, batch_kind, result)
                continue
            merged.update(result)
        return merged

    # Default to the narrative model (Sonnet) unless a specific model is passed.
    active_model = model or NARRATIVE_MODEL

    results: dict[str, str] = {}
    uncached: dict[str, tuple[str, dict]] = {}

    for key, (sec_type, data) in items.items():
        ck = _cache_key(sec_type, data, lang)
        try:
            cached = await _get_cached(ck)
            if cached:
                results[key] = cached
                continue
        except Exception:
            pass
        uncached[key] = (sec_type, data)

    if not uncached:
        logger.info("Batch narrate: all %d items cached", len(items))
        return results

    if use_mahadasha_prompt:
        system_prompt = _SYSTEM_PROMPT_MAHADASHA_HI if lang == "hi" else _SYSTEM_PROMPT_MAHADASHA_EN
    elif batch_kind == "varshaphal":
        system_prompt = _SYSTEM_PROMPT_VARSHAPHAL_HI if lang == "hi" else _SYSTEM_PROMPT_VARSHAPHAL_EN
    else:
        system_prompt = _SYSTEM_PROMPT_HI if lang == "hi" else _SYSTEM_PROMPT_EN

    parts = []
    for key, (sec_type, data) in uncached.items():
        item_prompt = _build_user_prompt(sec_type, data, lang)
        parts.append(f'=== "{key}" ===\n{item_prompt}')

    if use_mahadasha_prompt:
        instruction = (
            "Generate responses for each section below. "
            'Return ONLY a valid JSON object: {"key": {"experience": [...], "avoid": [...]}, ...}\n\n'
        )
        per_item_tokens = 600 if lang == "hi" else 420
    elif batch_kind == "varshaphal":
        instruction = (
            "Generate a structured annual forecast for each section below. "
            'Return ONLY a valid JSON object: '
            '{"key": {"overall": "...", "career": "...", "health": "...", "wealth": "...", "family": "..."}, ...}\n\n'
        )
        per_item_tokens = 900 if lang == "hi" else 650
    elif batch_kind == "remedy":
        if lang == "hi":
            instruction = (
                "नीचे दिए गए प्रत्येक उपाय के लिए एक संक्षिप्त वर्णन लिखें (2 अनुच्छेद, 55-80 शब्द प्रत्येक)। "
                "ये सभी उपाय एक ही व्यक्ति के लिए एक एकीकृत उपचार योजना हैं — जहां प्राकृतिक हो, "
                "एक दूसरे को संदर्भित करें (जैसे, यदि रत्न शुक्र के लिए है, मंत्र भी शुक्र-केंद्रित हो सकता है)। "
                "प्रत्येक उपाय इस व्यक्ति के ग्रहों की विशिष्ट कमजोरियों के लिए विशिष्ट होना चाहिए, सामान्य नहीं। "
                'केवल वैध JSON लौटाएं: {"key": "narrative...", ...}\n\n'
            )
        else:
            instruction = (
                "Generate a brief narrative for each remedy below (2 paragraphs, 70-95 words each). "
                "These remedies form ONE integrated plan for the same person — cross-reference where natural "
                "(e.g., if the gemstone is for Venus, the mantra section can also be Venus-focused). "
                "Each remedy should be specific to this person's actual planetary weaknesses, not generic. "
                'Return ONLY valid JSON: {"key": "narrative...", ...}\n\n'
            )
        per_item_tokens = 400 if lang == "hi" else 280
    else:
        instruction = (
            "Generate a narrative for each section below (2 paragraphs, 70-95 words each). "
            'Return ONLY a valid JSON object: {"key": "narrative text...", ...}\n\n'
        )
        per_item_tokens = 400 if lang == "hi" else 300

    batch_prompt = instruction + "\n\n".join(parts)
    max_tokens = min(len(uncached) * per_item_tokens, 16000)

    try:
        async with semaphore:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=active_model,
                    max_tokens=max_tokens,
                    temperature=0.7,
                    system=[{
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }],
                    messages=[{"role": "user", "content": batch_prompt}],
                ),
                timeout=150.0,
            )

        _log_usage(active_model, response.usage, f"batch:{label or batch_kind}", cost_sink)
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        if response.stop_reason == "max_tokens":
            logger.warning(
                "Batch narrate hit max_tokens (%d items, budget=%d); attempting salvage",
                len(uncached), max_tokens,
            )
            raw = _salvage_truncated_json(raw)

        batch_results = json.loads(raw)

        for key, narrative in batch_results.items():
            if key in uncached:
                sec_type, data = uncached[key]
                text = narrative if isinstance(narrative, str) else json.dumps(narrative, ensure_ascii=False)
                try:
                    await _set_cached(_cache_key(sec_type, data, lang), text)
                except Exception:
                    pass
                results[key] = text

        logger.info(
            "Batch narrate: %d/%d generated, %d cached",
            len(batch_results), len(uncached), len(items) - len(uncached),
        )

    except Exception:
        logger.warning("Batch narrate failed (%d items)", len(uncached), exc_info=True)

    return results


async def generate_narratives(
    kundli_data: KundliData,
    lang: str,
) -> dict[str, str]:
    if not settings.anthropic_api_key:
        logger.info("No ANTHROPIC_API_KEY configured, skipping narratives")
        return {}

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    planets_batch: dict[str, tuple[str, dict]] = {}
    misc_batch: dict[str, tuple[str, dict]] = {}
    md_journey_batch: dict[str, tuple[str, dict]] = {}
    yoga_batch: dict[str, tuple[str, dict]] = {}
    numerology_batch: dict[str, tuple[str, dict]] = {}
    remedy_batch: dict[str, tuple[str, dict]] = {}
    thematic_batch: dict[str, tuple[str, dict]] = {}
    varshaphal_batch: dict[str, tuple[str, dict]] = {}

    # --- Planet placements ---
    if kundli_data.planets:
        for planet in kundli_data.planets:
            if planet.name == "Ascendant":
                continue
            planets_batch[f"planet_{planet.name}"] = ("planet_placement", {
                "name": planet.name,
                "sign": planet.sign,
                "signLord": planet.signLord,
                "house": planet.house,
                "nakshatra": planet.nakshatra,
                "nakshatraLord": planet.nakshatraLord,
                "pada": planet.nakshatra_pad,
                "degree": round(planet.normDegree, 2),
                "isRetro": planet.isRetro,
            })

    # Outer planets (Uranus/Neptune/Pluto) narratives removed — not classical Vedic; the
    # outer_planets section is also unregistered in pdf_generator.py (cost cut).

    # --- Current Mahadasha ---
    if kundli_data.current_vdasha and kundli_data.current_vdasha.major:
        major = kundli_data.current_vdasha.major
        md_sign = ""
        md_house = ""
        if kundli_data.planets:
            for p in kundli_data.planets:
                if p.name == major.planet:
                    md_sign = p.sign
                    md_house = p.house
                    break
        minor_planet = ""
        if kundli_data.current_vdasha.minor:
            minor_planet = kundli_data.current_vdasha.minor.planet
        thematic_batch["current_mahadasha"] = ("mahadasha_period", {
            "major_planet": major.planet,
            "sign": md_sign,
            "house": md_house,
            "start": major.start,
            "end": major.end,
            "minor_planet": minor_planet,
        })

    # --- Raj Yogas ---
    if kundli_data.planets:
        from sections.yogas import _detect_yogas
        yogas = _detect_yogas(kundli_data.planets, kundli_data.houses)
        for yoga in yogas:
            if yoga.get("name") == "No Major Yoga Detected":
                continue
            yoga_data = {
                "name": yoga["name"],
                "planets": yoga["planets"],
                "house": yoga["house"],
                "effect": yoga["effect"],
                "description": yoga["description"],
            }
            yoga_batch[f"yoga_{yoga['name']}"] = ("raj_yoga", yoga_data)

    # --- Three Pillars of Self ---
    if kundli_data.planets:
        ascendant = next((p for p in kundli_data.planets if p.name == "Ascendant"), None)
        moon = next((p for p in kundli_data.planets if p.name == "Moon"), None)
        if ascendant:
            misc_batch["pillar_lagna"] = ("lagna_pillar", {
                "sign": ascendant.sign,
                "lord": ascendant.signLord,
                "nakshatra": ascendant.nakshatra,
                "nakshatraLord": ascendant.nakshatraLord,
                "degree": round(ascendant.normDegree, 2),
            })
        if moon:
            misc_batch["pillar_moon_rashi"] = ("moon_rashi_pillar", {
                "sign": moon.sign,
                "signLord": moon.signLord,
                "house": moon.house,
                "nakshatra": moon.nakshatra,
            })
            misc_batch["pillar_nakshatra"] = ("nakshatra_pillar", {
                "nakshatra": moon.nakshatra,
                "lord": moon.nakshatraLord,
                "pada": moon.nakshatra_pad,
                "sign": moon.sign,
            })

    # --- Sade Sati ---
    if kundli_data.sadhesati_life_details:
        details = kundli_data.sadhesati_life_details
        if isinstance(details, dict):
            details = details.get("sadhesati_details", [details])
        if isinstance(details, list):
            moon_sign = ""
            if kundli_data.planets:
                m = next((p for p in kundli_data.planets if p.name == "Moon"), None)
                if m:
                    moon_sign = m.sign
            phases_summary = [
                {
                    "type": p.get("phase", p.get("type", "")),
                    "saturn_sign": p.get("saturn_sign", p.get("sign", "")),
                    "date": p.get("date", p.get("start", p.get("start_date", ""))),
                }
                for p in details if isinstance(p, dict)
            ]
            if phases_summary:
                misc_batch["sade_sati_overview"] = ("sade_sati_overview", {
                    "moon_sign": moon_sign,
                    "is_active": bool(
                        kundli_data.sadhesati_current_status
                        and isinstance(kundli_data.sadhesati_current_status, dict)
                        and kundli_data.sadhesati_current_status.get("is_undergoing_sadhesati")
                    ),
                    "phases": phases_summary,
                })

    # --- Mahadasha Journey (uses different system prompt) ---
    # Only narrate the current mahadasha + next 2 — farther periods are low-value filler.
    # Must select the same window the renderer shows (sections/mahadasha_journey.py) so no
    # dasha card renders without a narrative.
    if kundli_data.major_vdasha and kundli_data.planets:
        from sections.mahadasha_journey import select_journey_dashas
        current_planet_en = ""
        if kundli_data.current_vdasha and kundli_data.current_vdasha.major:
            current_planet_en = planet_to_en(kundli_data.current_vdasha.major.planet)
        planet_map = {p.name: p for p in kundli_data.planets if p.name != "Ascendant"}
        for dasha in select_journey_dashas(kundli_data.major_vdasha, current_planet_en):
            # Normalize the (possibly Devanagari) dasha planet name to English so
            # the planet_map lookup works AND the narrative key matches the
            # renderer's key (sections/mahadasha_journey.py).
            planet_en = planet_to_en(dasha.planet)
            p = planet_map.get(planet_en)
            md_journey_batch[f"mahadasha_journey_{planet_en}"] = ("mahadasha_journey", {
                "planet": planet_en,
                "sign": p.sign if p else "Unknown",
                "house": p.house if p else "Unknown",
                "nakshatra": p.nakshatra if p else "Unknown",
                "start": dasha.start,
                "end": dasha.end,
                "isRetro": p.isRetro if p else "false",
            })

    # --- Numerology ---
    if kundli_data.numero_table and isinstance(kundli_data.numero_table, dict):
        req = kundli_data.request
        base_info = {"name": req.name, "day": req.day, "month": req.month, "year": req.year}

        radical = kundli_data.numero_table.get("radical_number")
        if radical is not None:
            numerology_batch["numero_personality_moolank"] = (
                "numerology_personality",
                {**base_info, "number_type": "Moolank (Radical Number)", "value": radical},
            )

        destiny = kundli_data.numero_table.get("destiny_number")
        if destiny is not None:
            numerology_batch["numero_personality_bhagyank"] = (
                "numerology_personality",
                {**base_info, "number_type": "Bhagyank (Life Path Number)", "value": destiny},
            )

        from sections.numerology_personality import chaldean_name_number, connection_number
        success = chaldean_name_number(req.name)
        numerology_batch["numero_personality_success"] = (
            "numerology_personality",
            {**base_info, "number_type": "Success Number (Chaldean Name)", "value": success},
        )
        conn = connection_number(req.day, req.month)
        numerology_batch["numero_personality_connection"] = (
            "numerology_personality",
            {**base_info, "number_type": "Connection Number", "value": conn},
        )

    # --- Remedies ---
    if kundli_data.rudraksha_suggestion:
        raw = kundli_data.rudraksha_suggestion
        suggestions = raw.get("rudraksha_suggestion", raw) if isinstance(raw, dict) else raw
        if isinstance(suggestions, list):
            mukhi_list = [int(s.get("mukhi", 0)) for s in suggestions if isinstance(s, dict) and s.get("mukhi")]
            if mukhi_list:
                remedy_batch["rudraksha_guidance"] = (
                    "rudraksha_guidance", {"mukhi_list": mukhi_list},
                )
                planet_str = ", ".join(s.get("planet", "") for s in suggestions if isinstance(s, dict))
                nak = ""
                if kundli_data.planets:
                    m = next((p for p in kundli_data.planets if p.name == "Moon"), None)
                    if m:
                        nak = m.nakshatra
                remedy_batch["rudraksha_personal"] = (
                    "rudraksha_personal",
                    {"mukhi_list": mukhi_list, "planets": planet_str, "nakshatra": nak},
                )

    if kundli_data.basic_gem_suggestion and kundli_data.houses:
        from sections.remedy_constants import SIGN_LORDS as _SL
        gems = kundli_data.basic_gem_suggestion
        lagna_sign = ""
        for h in (kundli_data.houses or []):
            hid = getattr(h, "house_id", None) or getattr(h, "house", 0)
            if isinstance(h, dict):
                hid = h.get("house_id", h.get("house", 0))
            if hid == 1:
                lagna_sign = getattr(h, "sign", "") or (h.get("sign", "") if isinstance(h, dict) else "")
                break
        for stone_type in ("life_stone", "lucky_stone", "fortune_stone"):
            stone = gems.get(stone_type, {})
            if stone and isinstance(stone, dict):
                remedy_batch[f"gemstone_{stone_type}"] = ("gemstone_benefit", {
                    "gem_name": stone.get("name", ""),
                    "planet": stone.get("planet", ""),
                    "type": stone_type.replace("_", " ").title(),
                    "lagna": lagna_sign,
                })

    if kundli_data.planets and kundli_data.houses:
        from sections.remedy_constants import (
            SIGN_LORDS as _SL2, TWELFTH_LORD_ISHTADEVATA as _TLI,
            PLANET_YANTRAS as _PY,
        )
        from sections.dignity import DEBILITATION as _DEB

        twelfth_lord = ""
        twelfth_sign = ""
        for h in kundli_data.houses:
            hid = getattr(h, "house_id", None) or getattr(h, "house", 0)
            if isinstance(h, dict):
                hid = h.get("house_id", h.get("house", 0))
            if hid == 12:
                twelfth_sign = getattr(h, "sign", "") or (h.get("sign", "") if isinstance(h, dict) else "")
                twelfth_lord = getattr(h, "sign_lord", "") or _SL2.get(twelfth_sign, "")
                if isinstance(h, dict) and not twelfth_lord:
                    twelfth_lord = h.get("sign_lord", _SL2.get(twelfth_sign, ""))
                break

        if twelfth_lord:
            ishta_info = _TLI.get(twelfth_lord, {})

        weak_planets = []
        weakest_score = 0
        weakest_planet = None
        for p in kundli_data.planets:
            if p.name == "Ascendant" or p.name not in _PY:
                continue
            score = 0
            if _DEB.get(p.name) == p.sign:
                score += 3
            if str(p.isRetro).lower() in ("true", "yes", "1"):
                score += 1
            if p.house in (6, 8, 12):
                score += 2
            if score > 0:
                dignity = "Debilitated" if _DEB.get(p.name) == p.sign else "Afflicted"
                weak_planets.append({"name": p.name, "dignity": dignity})
            if score > weakest_score:
                weakest_score = score
                weakest_planet = p

        weak_names = [wp["name"] for wp in weak_planets]
        remedy_batch["mantra_guidance"] = ("mantra_guidance", {
            "weak_planets": weak_names,
            "ishta_devata": ishta_info.get("deity", "") if twelfth_lord else "",
        })

        if weakest_planet:
            dignity = "Debilitated" if _DEB.get(weakest_planet.name) == weakest_planet.sign else "Afflicted"
            remedy_batch["yantra_guidance"] = ("yantra_guidance", {
                "yantra": _PY.get(weakest_planet.name, ""),
                "planet": weakest_planet.name,
                "dignity": dignity,
                "house": weakest_planet.house,
                "sign": weakest_planet.sign,
            })

        if weak_planets:
            remedy_batch["daan_guidance"] = ("daan_guidance", {
                "weak_planets": weak_planets,
            })

    # --- Thematic: Marriage, Career, Love, Spiritual, Rahu-Ketu ---
    if kundli_data.planets and kundli_data.houses:
        from sections.graha_profile import SIGN_LORDS as _SL3
        h7_sign = ""
        for h in kundli_data.houses:
            hid = getattr(h, "house_id", None) or getattr(h, "house", 0)
            if isinstance(h, dict):
                hid = h.get("house_id", h.get("house", 0))
            if hid == 7:
                h7_sign = getattr(h, "sign", "") or (h.get("sign", "") if isinstance(h, dict) else "")
                break
        h7_lord = _SL3.get(h7_sign, "")
        venus = next((p for p in kundli_data.planets if p.name == "Venus"), None)
        h7_lord_p = next((p for p in kundli_data.planets if p.name == h7_lord), None)
        p_in_7 = [p.name for p in kundli_data.planets if p.house == 7 and p.name != "Ascendant"]
        thematic_batch["marriage_timing"] = ("marriage_timing", {
            "seventh_sign": h7_sign,
            "seventh_lord": h7_lord,
            "seventh_lord_house": h7_lord_p.house if h7_lord_p else "",
            "seventh_lord_sign": h7_lord_p.sign if h7_lord_p else "",
            "venus_house": venus.house if venus else "",
            "venus_sign": venus.sign if venus else "",
            "planets_in_7": ", ".join(p_in_7) if p_in_7 else "None",
        })

    if kundli_data.varshaphal_details:
        vd = kundli_data.varshaphal_details
        vm_raw = kundli_data.varshaphal_muntha
        if isinstance(vm_raw, list):
            vm = next((x for x in vm_raw if isinstance(x, dict)), {})
        elif isinstance(vm_raw, dict):
            vm = vm_raw
        else:
            vm = {}
        vp_data: dict[str, Any] = {
            "year": vd.get("year", ""),
            "ascendant": vd.get("varshaphal_ascendant", ""),
            "muntha_sign": vd.get("muntha_sign", ""),
            "varshesh": vd.get("varshesh", ""),
            "varshesha_strength": vd.get("varshesha_strength", ""),
            "muntha_house": vm.get("muntha_house", ""),
            "muntha_lord": vm.get("muntha_lord", ""),
        }
        if kundli_data.varshaphal_yoga:
            names = [y.get("yoga_name", "") for y in kundli_data.varshaphal_yoga
                     if isinstance(y, dict) and y.get("yoga_name")]
            vp_data["yogas"] = ", ".join(names) if names else "None"
        varshaphal_batch["varshaphal"] = ("varshaphal", vp_data)

    if kundli_data.planets and kundli_data.houses:
        from sections.graha_profile import SIGN_LORDS as _SL4
        h10_sign = ""
        for h in kundli_data.houses:
            hid = getattr(h, "house_id", None) or getattr(h, "house", 0)
            if isinstance(h, dict):
                hid = h.get("house_id", h.get("house", 0))
            if hid == 10:
                h10_sign = getattr(h, "sign", "") or (h.get("sign", "") if isinstance(h, dict) else "")
                break
        h10_lord = _SL4.get(h10_sign, "")
        h10_lord_p = next((p for p in kundli_data.planets if p.name == h10_lord), None)
        sun = next((p for p in kundli_data.planets if p.name == "Sun"), None)
        saturn = next((p for p in kundli_data.planets if p.name == "Saturn"), None)
        cp_data = {
            "tenth_sign": h10_sign,
            "tenth_lord": h10_lord,
            "tenth_lord_house": h10_lord_p.house if h10_lord_p else "",
            "sun_house": sun.house if sun else "",
            "sun_sign": sun.sign if sun else "",
            "saturn_house": saturn.house if saturn else "",
            "saturn_sign": saturn.sign if saturn else "",
            "amatyakaraka": "",
        }
        from sections.career_path import _compute_amatyakaraka
        ak = _compute_amatyakaraka(kundli_data.planets)
        if ak:
            cp_data["amatyakaraka"] = f"{ak['name']} in {ak['sign']} (House {ak['house']})"
        thematic_batch["career_path"] = ("career_path", cp_data)

    if kundli_data.planets and kundli_data.houses:
        from sections.graha_profile import SIGN_LORDS as _SLM
        h4_sign = ""
        for h in kundli_data.houses:
            hid = getattr(h, "house_id", None) or getattr(h, "house", 0)
            if isinstance(h, dict):
                hid = h.get("house_id", h.get("house", 0))
            if hid == 4:
                h4_sign = getattr(h, "sign", "") or (h.get("sign", "") if isinstance(h, dict) else "")
                break
        h4_lord = _SLM.get(h4_sign, "")
        h4_lord_p = next((p for p in kundli_data.planets if p.name == h4_lord), None)
        venus_mc = next((p for p in kundli_data.planets if p.name == "Venus"), None)
        mars_mc = next((p for p in kundli_data.planets if p.name == "Mars"), None)
        thematic_batch["material_comforts"] = ("material_comforts", {
            "fourth_sign": h4_sign,
            "fourth_lord": h4_lord,
            "fourth_lord_house": h4_lord_p.house if h4_lord_p else "",
            "venus_house": venus_mc.house if venus_mc else "",
            "venus_sign": venus_mc.sign if venus_mc else "",
            "mars_house": mars_mc.house if mars_mc else "",
            "mars_sign": mars_mc.sign if mars_mc else "",
        })

    if kundli_data.planets and kundli_data.houses:
        from sections.graha_profile import SIGN_LORDS as _SL6
        h9_sign = ""
        h12_sign_sp = ""
        for h in kundli_data.houses:
            hid = getattr(h, "house_id", None) or getattr(h, "house", 0)
            if isinstance(h, dict):
                hid = h.get("house_id", h.get("house", 0))
            if hid == 9:
                h9_sign = getattr(h, "sign", "") or (h.get("sign", "") if isinstance(h, dict) else "")
            if hid == 12:
                h12_sign_sp = getattr(h, "sign", "") or (h.get("sign", "") if isinstance(h, dict) else "")
        jup = next((p for p in kundli_data.planets if p.name == "Jupiter"), None)
        ket = next((p for p in kundli_data.planets if p.name == "Ketu"), None)
        from sections.spiritual_potential import _compute_atmakaraka
        atma = _compute_atmakaraka(kundli_data.planets)
        thematic_batch["spiritual_potential"] = ("spiritual_potential", {
            "ninth_sign": h9_sign,
            "ninth_lord": _SL6.get(h9_sign, ""),
            "twelfth_sign": h12_sign_sp,
            "twelfth_lord": _SL6.get(h12_sign_sp, ""),
            "jupiter_house": jup.house if jup else "",
            "jupiter_sign": jup.sign if jup else "",
            "ketu_house": ket.house if ket else "",
            "ketu_sign": ket.sign if ket else "",
            "atmakaraka": f"{atma['name']} in {atma['sign']} (House {atma['house']})" if atma else "Not computed",
        })

    if kundli_data.planets:
        rahu_p = next((p for p in kundli_data.planets if p.name == "Rahu"), None)
        ketu_p = next((p for p in kundli_data.planets if p.name == "Ketu"), None)
        if rahu_p and ketu_p:
            from sections.rahu_ketu_analysis import _get_axis_key
            thematic_batch["rahu_ketu_analysis"] = ("rahu_ketu_analysis", {
                "rahu_house": rahu_p.house,
                "rahu_sign": rahu_p.sign,
                "rahu_nakshatra": rahu_p.nakshatra,
                "ketu_house": ketu_p.house,
                "ketu_sign": ketu_p.sign,
                "ketu_nakshatra": ketu_p.nakshatra,
                "axis": _get_axis_key(rahu_p.house, ketu_p.house),
            })

    # --- Fire all batches in parallel ---
    # Cost lever: formulaic batches (planets, numerology) use Haiku (3x cheaper);
    # flagship batches (md_journey, thematic, yoga, remedy, misc) stay on Sonnet.
    # Expand the set after A/B verifying quality holds. Kill-switch in config.
    simple_model = (
        SIMPLE_NARRATIVE_MODEL
        if settings.use_haiku_for_simple_narratives
        else NARRATIVE_MODEL
    )
    cost_sink: list[float] = []
    batch_coros = []
    if planets_batch:
        batch_coros.append(_batch_narrate(planets_batch, lang, client, semaphore, label="planets", cost_sink=cost_sink, model=simple_model))
    if misc_batch:
        batch_coros.append(_batch_narrate(misc_batch, lang, client, semaphore, label="misc", cost_sink=cost_sink))
    if md_journey_batch:
        batch_coros.append(_batch_narrate(md_journey_batch, lang, client, semaphore, use_mahadasha_prompt=True, label="md_journey", cost_sink=cost_sink))
    if yoga_batch:
        batch_coros.append(_batch_narrate(yoga_batch, lang, client, semaphore, label="yoga", cost_sink=cost_sink))
    if numerology_batch:
        batch_coros.append(_batch_narrate(numerology_batch, lang, client, semaphore, label="numerology", cost_sink=cost_sink, model=simple_model))
    if remedy_batch:
        batch_coros.append(_batch_narrate(remedy_batch, lang, client, semaphore, batch_kind="remedy", label="remedy", cost_sink=cost_sink))
    if thematic_batch:
        batch_coros.append(_batch_narrate(thematic_batch, lang, client, semaphore, label="thematic", cost_sink=cost_sink))
    if varshaphal_batch:
        batch_coros.append(_batch_narrate(varshaphal_batch, lang, client, semaphore, batch_kind="varshaphal", label="varshaphal", cost_sink=cost_sink))

    if not batch_coros:
        return {}

    gathered = await asyncio.gather(*batch_coros, return_exceptions=True)

    results: dict[str, str] = {}
    for result in gathered:
        if isinstance(result, dict):
            results.update(result)
        elif isinstance(result, Exception):
            logger.warning("Batch failed: %s", result)

    total_items = sum(len(b) for b in [
        planets_batch, misc_batch, md_journey_batch, yoga_batch,
        numerology_batch, remedy_batch, thematic_batch, varshaphal_batch,
    ])
    logger.info("Narratives generated: %d/%d successful (%d batches)", len(results), total_items, len(batch_coros))
    logger.info("COST TOTAL narratives lang=%s model=%s => $%.4f", lang, MODEL, sum(cost_sink))
    return results


_TRANSLATE_SYSTEM_PROMPT = """\
You are a professional Hindi translator specializing in Vedic astrology texts.
Translate the given English text to pure, fluent Hindi (Devanagari script).
Keep astrological terms in their Sanskrit/Hindi equivalents (e.g., graha, rashi, bhava, nakshatra).
Preserve the meaning exactly — do not add, remove, or embellish content.
Do not translate proper nouns (planet names like Sun, Moon, Mars may be kept or use Hindi: सूर्य, चंद्र, मंगल).

You will receive a JSON object where keys are identifiers and values are English text.
Return ONLY a valid JSON object with the same keys and Hindi-translated values.
No markdown, no code fences, no explanation — just the JSON."""


def _extract_texts(data: dict | list | None, prefix: str = "") -> dict[str, str]:
    """Recursively extract string values from nested dict/list into a flat {path: text} dict."""
    texts: dict[str, str] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, str) and len(v) > 20:
                texts[path] = v
            elif isinstance(v, (dict, list)):
                texts.update(_extract_texts(v, path))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            path = f"{prefix}[{i}]"
            if isinstance(item, str) and len(item) > 20:
                texts[path] = item
            elif isinstance(item, (dict, list)):
                texts.update(_extract_texts(item, path))
    return texts


def _inject_texts(data: dict | list, translations: dict[str, str], prefix: str = "") -> None:
    """Inject translated texts back into the original nested structure in-place."""
    if isinstance(data, dict):
        for k in list(data.keys()):
            path = f"{prefix}.{k}" if prefix else k
            if path in translations:
                data[k] = translations[path]
            elif isinstance(data[k], (dict, list)):
                _inject_texts(data[k], translations, path)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            path = f"{prefix}[{i}]"
            if path in translations and isinstance(item, str):
                data[i] = translations[path]
            elif isinstance(item, (dict, list)):
                _inject_texts(item, translations, path)


async def _translate_batch(
    texts: dict[str, str],
    client: AsyncAnthropic,
    semaphore: asyncio.Semaphore,
    cost_sink: list[float] | None = None,
) -> dict[str, str]:
    if not texts:
        return {}

    cache_key = _cache_key("translate_hi", texts, "hi")

    try:
        cached = await _get_cached(cache_key)
        if cached:
            logger.debug("Translation cache hit (%d texts)", len(texts))
            return json.loads(cached)
    except Exception:
        logger.warning("Translation cache read failed", exc_info=True)

    user_prompt = json.dumps(texts, ensure_ascii=False, indent=2)
    translation_model = TRANSLATION_MODEL if settings.use_haiku_for_translation else NARRATIVE_MODEL
    logger.info("Translation batch: model=%s, items=%d", translation_model, len(texts))

    try:
        async with semaphore:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=translation_model,
                    max_tokens=8192,
                    temperature=0.3,
                    system=[{
                        "type": "text",
                        "text": _TRANSLATE_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }],
                    messages=[{"role": "user", "content": user_prompt}],
                ),
                timeout=60.0,
            )

        _log_usage(translation_model, response.usage, "translate", cost_sink)
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        if response.stop_reason == "max_tokens":
            logger.warning(
                "Translation hit max_tokens (%d items); attempting salvage", len(texts),
            )
            raw = _salvage_truncated_json(raw)

        try:
            translated = json.loads(raw)
        except json.JSONDecodeError:
            # Last-ditch salvage even if stop_reason wasn't max_tokens.
            logger.warning("Translation JSON parse failed; attempting salvage", exc_info=True)
            translated = json.loads(_salvage_truncated_json(raw))

        try:
            await _set_cached(cache_key, json.dumps(translated, ensure_ascii=False))
        except Exception:
            logger.warning("Translation cache write failed", exc_info=True)

        logger.info("Translated %d texts to Hindi", len(translated))
        return translated

    except Exception:
        logger.warning("Translation batch failed", exc_info=True)
        return {}


async def _translate_chunked(
    texts: dict[str, str],
    client: AsyncAnthropic,
    semaphore: asyncio.Semaphore,
    cost_sink: list[float] | None = None,
    chunk_size: int = 4,
) -> dict[str, str]:
    """Split a large text dict into chunks and translate each separately.

    Bounds each API call's output so it fits under max_tokens and the timeout.
    A failure in one chunk loses only that chunk, not the whole batch. Chunks
    run concurrently (bounded by the shared semaphore).
    """
    if not texts:
        return {}

    items = list(texts.items())
    chunks = [dict(items[i:i + chunk_size]) for i in range(0, len(items), chunk_size)]

    if len(chunks) == 1:
        return await _translate_batch(texts, client, semaphore, cost_sink)

    logger.info("Translation: splitting %d texts into %d chunks of ~%d",
                len(texts), len(chunks), chunk_size)

    chunk_results = await asyncio.gather(
        *(_translate_batch(chunk, client, semaphore, cost_sink) for chunk in chunks),
        return_exceptions=True,
    )

    merged: dict[str, str] = {}
    for i, result in enumerate(chunk_results):
        if isinstance(result, Exception):
            logger.warning("Translation chunk %d failed: %s", i, result)
            continue
        merged.update(result)
    return merged


# API report fields (ascendant विवरण, nakshatra चरित्र/शिक्षा…) run 10-12 lines. Hard-cap each
# field by character budget before translating so Haiku processes and returns far fewer tokens.
# A char cap is deterministic — unlike sentence counting, it still trims run-on report text that
# has few .!? terminators (which was letting most fields through untruncated).
_REPORT_MAX_CHARS = 350


def _truncate_report(text: str, max_chars: int = _REPORT_MAX_CHARS) -> str:
    """Hard-cap English report text before translation, ending on a sentence boundary when possible."""
    if not text or len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    last = max(cut.rfind("."), cut.rfind("!"), cut.rfind("?"))
    return (cut[: last + 1] if last >= max_chars // 2 else cut).strip()


async def translate_reports(kundli_data: KundliData, lang: str) -> None:
    if lang != "hi" or not settings.anthropic_api_key:
        return

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    batch1_texts: dict[str, str] = {}
    if kundli_data.general_ascendant_report:
        batch1_texts.update(
            _extract_texts(kundli_data.general_ascendant_report, "asc")
        )
    if kundli_data.general_nakshatra_report:
        batch1_texts.update(
            _extract_texts(kundli_data.general_nakshatra_report, "nak")
        )
    # Shorten these verbose report fields before translation (cost + length).
    batch1_texts = {k: _truncate_report(v) for k, v in batch1_texts.items()}

    batch2_texts: dict[str, str] = {}
    if kundli_data.general_house_reports:
        batch2_texts.update(
            _extract_texts(kundli_data.general_house_reports, "house")
        )
    # House reports run 10-12 lines each; truncate like batch1 to cut translation output cost.
    batch2_texts = {k: _truncate_report(v) for k, v in batch2_texts.items()}

    batch3_texts: dict[str, str] = {}
    if kundli_data.general_rashi_reports:
        batch3_texts.update(
            _extract_texts(kundli_data.general_rashi_reports, "rashi")
        )
    # Rashi reports are similarly verbose; truncate before translation.
    batch3_texts = {k: _truncate_report(v) for k, v in batch3_texts.items()}

    cost_sink: list[float] = []
    results = await asyncio.gather(
        _translate_chunked(batch1_texts, client, semaphore, cost_sink),
        _translate_chunked(batch2_texts, client, semaphore, cost_sink),
        _translate_chunked(batch3_texts, client, semaphore, cost_sink),
        return_exceptions=True,
    )

    batch1_result = results[0] if not isinstance(results[0], Exception) else {}
    batch2_result = results[1] if not isinstance(results[1], Exception) else {}
    batch3_result = results[2] if not isinstance(results[2], Exception) else {}

    if batch1_result:
        asc_translations = {k[4:]: v for k, v in batch1_result.items() if k.startswith("asc.")}
        nak_translations = {k[4:]: v for k, v in batch1_result.items() if k.startswith("nak.")}
        if asc_translations and kundli_data.general_ascendant_report:
            _inject_texts(kundli_data.general_ascendant_report, asc_translations)
        if nak_translations and kundli_data.general_nakshatra_report:
            _inject_texts(kundli_data.general_nakshatra_report, nak_translations)

    if batch2_result and kundli_data.general_house_reports:
        house_translations = {k[6:]: v for k, v in batch2_result.items() if k.startswith("house.")}
        _inject_texts(kundli_data.general_house_reports, house_translations)

    if batch3_result and kundli_data.general_rashi_reports:
        rashi_translations = {k[6:]: v for k, v in batch3_result.items() if k.startswith("rashi.")}
        _inject_texts(kundli_data.general_rashi_reports, rashi_translations)

    translated_count = sum(len(r) for r in (batch1_result, batch2_result, batch3_result) if isinstance(r, dict))
    logger.info("Report translation complete: %d fields translated to Hindi", translated_count)
    logger.info("COST TOTAL translation lang=%s => $%.4f", lang, sum(cost_sink))

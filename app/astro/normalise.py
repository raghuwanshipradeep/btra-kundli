"""Canonical name resolution and the 27-nakshatra master table.

Two jobs:

1. **Kill defect #7.** The reference report printed "Sun Nakshatra: Bharni — details
   unavailable" because a lookup key missed by one letter. Every nakshatra name that has ever
   come back from AstrologyAPI — English, Tamil transliteration, Devanagari, or a typo — must
   resolve to one of 27 canonical entries or raise. There is no third outcome, and no code
   path that renders a name without its data.

2. **Prefer longitude over labels.** The API returns ``fullDegree`` (sidereal longitude) as
   well as a ``nakshatra`` string, and the string arrives in whatever language the request
   asked for. Longitude is language-independent and exact, so ``nakshatra_at()`` derives the
   nakshatra and pada from the degree; the alias map exists to reconcile the API's own label
   and flag a disagreement, not to be the primary source.

Deliberately standalone: it does not import from ``sections`` (which pulls in Jinja2) so the
astrology layer stays free of rendering dependencies. The planet/sign alias tables here
overlap with ``sections/__init__.py`` by design.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.astro.enums import ASCENDANT, Graha, Rashi

# A nakshatra spans 13°20', a pada spans 3°20'.
NAKSHATRA_SPAN = 360.0 / 27.0
PADA_SPAN = NAKSHATRA_SPAN / 4.0


class NameResolutionError(ValueError):
    """Raised when a name cannot be resolved. Deliberately fatal: a silently-unresolved
    nakshatra is exactly the defect this module exists to prevent."""


@dataclass(frozen=True, slots=True)
class Nakshatra:
    """One of the 27 lunar mansions, with the attributes §15 renders.

    ``index`` is 1-based (Ashwini = 1) to match every printed table and the API.
    """

    index: int
    en: str
    hi: str
    lord: Graha
    deity_en: str
    deity_hi: str
    symbol_en: str
    symbol_hi: str
    gana: str      # deva | manushya | rakshasa
    yoni: str      # animal, for Yoni Kuta in match-making
    nadi: str      # adi | madhya | antya
    aliases: tuple[str, ...] = ()

    @property
    def start_longitude(self) -> float:
        return (self.index - 1) * NAKSHATRA_SPAN

    @property
    def end_longitude(self) -> float:
        return self.index * NAKSHATRA_SPAN

    def label(self, lang: str) -> str:
        return self.hi if lang == "hi" else self.en

    def deity(self, lang: str) -> str:
        return self.deity_hi if lang == "hi" else self.deity_en

    def symbol(self, lang: str) -> str:
        return self.symbol_hi if lang == "hi" else self.symbol_en


# The lord sequence below is the Vimshottari order (Ketu, Venus, Sun, Moon, Mars, Rahu,
# Jupiter, Saturn, Mercury) repeated three times — it is what makes the dasha balance
# computable from the Moon's nakshatra, so it must not be "tidied".
NAKSHATRAS: tuple[Nakshatra, ...] = (
    Nakshatra(1, "Ashwini", "अश्विनी", Graha.KETU,
              "Ashwini Kumaras", "अश्विनी कुमार", "horse's head", "अश्व मुख",
              "deva", "horse", "adi", ("Ashvini", "Aswini", "Aswathy", "Ashwathy")),
    Nakshatra(2, "Bharani", "भरणी", Graha.VENUS,
              "Yama", "यम", "vulva / bearer", "योनि",
              "manushya", "elephant", "madhya", ("Bharni", "Barani", "Bharanee")),
    Nakshatra(3, "Krittika", "कृत्तिका", Graha.SUN,
              "Agni", "अग्नि", "razor / flame", "छुरा",
              "rakshasa", "sheep", "antya", ("Kritika", "Karthigai", "Karthika", "Kruttika")),
    Nakshatra(4, "Rohini", "रोहिणी", Graha.MOON,
              "Prajapati Brahma", "प्रजापति ब्रह्मा", "ox-cart", "शकट",
              "manushya", "serpent", "antya", ("Rohinee",)),
    Nakshatra(5, "Mrigashira", "मृगशिरा", Graha.MARS,
              "Soma", "सोम", "deer's head", "मृग मुख",
              "deva", "serpent", "madhya",
              ("Mrigashirsha", "Mrigasira", "Mrigashiras", "Mrigasheersham",
               "Mrigashirisham", "Makayiram", "Mrugasira")),
    Nakshatra(6, "Ardra", "आर्द्रा", Graha.RAHU,
              "Rudra", "रुद्र", "teardrop", "अश्रु",
              "manushya", "dog", "adi", ("Aardra", "Arudra", "Thiruvathirai")),
    Nakshatra(7, "Punarvasu", "पुनर्वसु", Graha.JUPITER,
              "Aditi", "अदिति", "quiver of arrows", "तूणीर",
              "deva", "cat", "adi", ("Punarpoosam", "Punarvasoo", "Punartham")),
    Nakshatra(8, "Pushya", "पुष्य", Graha.SATURN,
              "Brihaspati", "बृहस्पति", "cow's udder", "गो-स्तन",
              "deva", "sheep", "madhya", ("Pushyami", "Poosam", "Pooyam", "Pushyam")),
    Nakshatra(9, "Ashlesha", "आश्लेषा", Graha.MERCURY,
              "the Nagas", "नाग", "coiled serpent", "कुंडलित सर्प",
              "rakshasa", "cat", "antya", ("Aslesha", "Ayilyam", "Ashlesa")),
    Nakshatra(10, "Magha", "मघा", Graha.KETU,
              "the Pitris", "पितृगण", "royal throne", "राजसिंहासन",
              "rakshasa", "rat", "antya", ("Magham", "Makam", "Magam")),
    Nakshatra(11, "Purva Phalguni", "पूर्वा फाल्गुनी", Graha.VENUS,
              "Bhaga", "भग", "front legs of a bed", "शय्या का अग्र भाग",
              "manushya", "rat", "madhya",
              ("Poorva Phalguni", "Pubba", "Pooram", "Purvaphalguni", "Purva Falguni")),
    Nakshatra(12, "Uttara Phalguni", "उत्तरा फाल्गुनी", Graha.SUN,
              "Aryaman", "अर्यमन", "back legs of a bed", "शय्या का पश्च भाग",
              "manushya", "cow", "adi",
              ("Uthiram", "Uttaraphalguni", "Uttara Falguni", "Uttram")),
    Nakshatra(13, "Hasta", "हस्त", Graha.MOON,
              "Savitar", "सवितृ", "open hand", "हस्त",
              "deva", "buffalo", "adi", ("Hastham", "Hastam", "Hasth")),
    Nakshatra(14, "Chitra", "चित्रा", Graha.MARS,
              "Vishvakarma", "विश्वकर्मा", "bright jewel", "मणि",
              "rakshasa", "tiger", "madhya", ("Chithirai", "Chitta", "Chithra")),
    Nakshatra(15, "Swati", "स्वाति", Graha.RAHU,
              "Vayu", "वायु", "young shoot in the wind", "अंकुर",
              "deva", "buffalo", "antya", ("Swathi", "Chothi", "Svati", "Sowathi")),
    Nakshatra(16, "Vishakha", "विशाखा", Graha.JUPITER,
              "Indra and Agni", "इंद्राग्नि", "triumphal arch", "तोरण",
              "rakshasa", "tiger", "antya", ("Vishakam", "Visakha", "Vishaka", "Vishakham")),
    Nakshatra(17, "Anuradha", "अनुराधा", Graha.SATURN,
              "Mitra", "मित्र", "lotus", "कमल",
              "deva", "deer", "madhya", ("Anusham", "Anuradh", "Anizham")),
    Nakshatra(18, "Jyeshtha", "ज्येष्ठा", Graha.MERCURY,
              "Indra", "इंद्र", "circular amulet", "कुंडल",
              "rakshasa", "deer", "adi", ("Jyestha", "Kettai", "Jyeshta", "Ketta")),
    Nakshatra(19, "Mula", "मूल", Graha.KETU,
              "Nirriti", "निर्ऋति", "tied bunch of roots", "मूल",
              "rakshasa", "dog", "adi", ("Moola", "Moolam", "Mool")),
    Nakshatra(20, "Purva Ashadha", "पूर्वाषाढ़ा", Graha.VENUS,
              "Apas", "आपः", "elephant tusk / fan", "पंखा",
              "manushya", "monkey", "madhya",
              ("Purvashada", "Poorvashada", "Pooradam", "Purva Ashada", "Purvashadha")),
    Nakshatra(21, "Uttara Ashadha", "उत्तराषाढ़ा", Graha.SUN,
              "the Vishvadevas", "विश्वेदेवाः", "elephant tusk", "गज दंत",
              "manushya", "mongoose", "antya",
              ("Uttarashada", "Uthiradam", "Uttara Ashada", "Uttarashadha")),
    Nakshatra(22, "Shravana", "श्रवण", Graha.MOON,
              "Vishnu", "विष्णु", "three footprints", "त्रिपद",
              "deva", "monkey", "antya", ("Sravana", "Thiruvonam", "Onam", "Shravan")),
    Nakshatra(23, "Dhanishta", "धनिष्ठा", Graha.MARS,
              "the Vasus", "वसुगण", "drum", "मृदंग",
              "rakshasa", "lion", "madhya", ("Dhanishtha", "Avittam", "Dhanista", "Sravista")),
    Nakshatra(24, "Shatabhisha", "शतभिषा", Graha.RAHU,
              "Varuna", "वरुण", "empty circle", "रिक्त वृत्त",
              "rakshasa", "horse", "adi",
              ("Satabhisha", "Sathayam", "Shatataraka", "Chathayam", "Shatabhishaj")),
    Nakshatra(25, "Purva Bhadrapada", "पूर्वा भाद्रपद", Graha.JUPITER,
              "Aja Ekapada", "अज एकपाद", "front of a funeral cot", "शय्या का अग्र",
              "manushya", "lion", "adi",
              ("Purvabhadra", "Poorattathi", "Purva Bhadra", "Pooruruttathi")),
    Nakshatra(26, "Uttara Bhadrapada", "उत्तरा भाद्रपद", Graha.SATURN,
              "Ahir Budhnya", "अहिर्बुध्न्य", "back of a funeral cot", "शय्या का पश्च",
              "manushya", "cow", "madhya",
              ("Uttarabhadra", "Uthirattathi", "Uttara Bhadra", "Uthrattathi")),
    Nakshatra(27, "Revati", "रेवती", Graha.MERCURY,
              "Pushan", "पूषन", "fish / drum", "मीन",
              "deva", "elephant", "antya", ("Revathi", "Revathy", "Rewati")),
)

assert len(NAKSHATRAS) == 27, "The nakshatra table must have exactly 27 entries"


def _squash(name: str) -> str:
    """Reduce a name to a comparison key: fold accents, drop everything that is not a
    letter or Devanagari codepoint, lowercase.

    This is what makes "Purva Ashadha", "Purvashada", "purva-ashadha" and "PURVA ASHADA"
    the same key without needing an alias entry for each. Devanagari is preserved as-is
    (NFC-normalised) because its spelling variants are genuinely different strings and
    are listed explicitly instead.
    """
    if not name:
        return ""
    text = unicodedata.normalize("NFC", str(name)).strip().lower()
    # Strip Latin diacritics used in academic transliteration (Kṛttikā -> krttika).
    decomposed = unicodedata.normalize("NFD", text)
    text = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-zऀ-ॿ]", "", unicodedata.normalize("NFC", text))


def _consonant_skeleton(name: str) -> str:
    """Second-tier key: the consonant skeleton of a Latin transliteration.

    Sanskrit transliterations disagree on vowels and sibilants — Kṛttikā vs Krittika,
    Mṛgaśira vs Mrigashira, Aśleṣā vs Ashlesha. Stripping diacritics is not enough because
    the vowel itself differs ("krttika" vs "krittika"). Folding sibilants together and then
    dropping vowels makes those pairs identical while keeping the 27 entries distinct.

    Returns "" for Devanagari input — the skeleton idea only applies to Latin script, and
    Devanagari variants are listed explicitly as aliases instead.
    """
    key = _squash(name)
    if not key or not key.isascii():
        return ""
    folded = key.replace("sh", "s").replace("chh", "ch").replace("ksh", "ks")
    skeleton = re.sub(r"[aeiou]", "", folded)
    # Collapse doubled consonants ("krttk" and "krtk" should agree).
    return re.sub(r"(.)\1+", r"\1", skeleton)


def _build_nakshatra_lookup() -> tuple[dict[str, Nakshatra], dict[str, Nakshatra]]:
    exact: dict[str, Nakshatra] = {}
    skeletons: dict[str, set[int]] = {}
    for nak in NAKSHATRAS:
        for variant in (nak.en, nak.hi, *nak.aliases):
            key = _squash(variant)
            if key and key not in exact:
                exact[key] = nak
            skeleton = _consonant_skeleton(variant)
            if skeleton:
                skeletons.setdefault(skeleton, set()).add(nak.index)

    # Only keep skeletons that identify exactly one nakshatra. An ambiguous skeleton must
    # raise rather than silently pick one of two mansions — a wrong nakshatra is worse than
    # a missing one, which is the whole premise of this module.
    by_index = {nak.index: nak for nak in NAKSHATRAS}
    unique = {
        skeleton: by_index[next(iter(indices))]
        for skeleton, indices in skeletons.items()
        if len(indices) == 1
    }
    return exact, unique


_NAKSHATRA_BY_KEY, _NAKSHATRA_BY_SKELETON = _build_nakshatra_lookup()


def resolve_nakshatra(name: str) -> Nakshatra:
    """Resolve any nakshatra label to its canonical entry.

    Resolution is exact-or-raise, in three tiers of decreasing directness: the squashed key,
    a prefix match (the API occasionally appends a pada or truncates a long compound name),
    then the unambiguous consonant skeleton. Raises rather than returning None — a caller
    that cannot name the nakshatra must not proceed to render a page about it.
    """
    key = _squash(name)
    if not key:
        raise NameResolutionError("Empty nakshatra name")
    if key in _NAKSHATRA_BY_KEY:
        return _NAKSHATRA_BY_KEY[key]

    # Prefix / containment fallback, longest candidate first so "uttaraashadha" cannot be
    # captured by a shorter unrelated key.
    candidates = sorted(_NAKSHATRA_BY_KEY, key=len, reverse=True)
    for candidate in candidates:
        if key.startswith(candidate) or candidate.startswith(key):
            return _NAKSHATRA_BY_KEY[candidate]
    for candidate in candidates:
        if candidate in key:
            return _NAKSHATRA_BY_KEY[candidate]

    skeleton = _consonant_skeleton(name)
    if skeleton and skeleton in _NAKSHATRA_BY_SKELETON:
        return _NAKSHATRA_BY_SKELETON[skeleton]

    raise NameResolutionError(f"Unrecognised nakshatra name: {name!r} (key={key!r})")


def try_resolve_nakshatra(name: str) -> Nakshatra | None:
    """Non-raising variant, for reconciling an API label against a longitude-derived value."""
    try:
        return resolve_nakshatra(name)
    except NameResolutionError:
        return None


def normalise_longitude(longitude: float) -> float:
    """Fold any longitude into [0, 360). Guards against an API returning 360.0 or a negative."""
    return float(longitude) % 360.0


def nakshatra_at(longitude: float) -> tuple[Nakshatra, int]:
    """Return (nakshatra, pada) for a sidereal longitude. Pada is 1-4.

    This is the authoritative derivation — language-independent and exact. Compare an API
    label against it with ``resolve_nakshatra``; never the other way round.
    """
    lon = normalise_longitude(longitude)
    index = int(lon // NAKSHATRA_SPAN)          # 0-26
    offset = lon - index * NAKSHATRA_SPAN
    pada = int(offset // PADA_SPAN) + 1         # 1-4
    return NAKSHATRAS[index], min(pada, 4)


def nakshatra_elapsed_fraction(longitude: float) -> float:
    """How far through its nakshatra a longitude sits, as 0.0-1.0.

    The Vimshottari balance at birth is ``(1 - this) * lord_period``, so this is the single
    number the whole dasha timeline hangs off.
    """
    lon = normalise_longitude(longitude)
    offset = lon % NAKSHATRA_SPAN
    return offset / NAKSHATRA_SPAN


# --- Rashi ------------------------------------------------------------------------------

_RASHI_ALIASES: dict[str, Rashi] = {}
for _r in Rashi:
    for _variant in (_r.en, _r.hi):
        _RASHI_ALIASES[_squash(_variant)] = _r
# Tamil transliterations, which the API returns for some south-Indian locales.
for _tamil, _rashi in {
    "Mesham": Rashi.ARIES, "Rishabam": Rashi.TAURUS, "Rishaba": Rashi.TAURUS,
    "Midhunam": Rashi.GEMINI, "Kadagam": Rashi.CANCER, "Katakam": Rashi.CANCER,
    "Simmam": Rashi.LEO, "Kanni": Rashi.VIRGO, "Kanya": Rashi.VIRGO,
    "Thulam": Rashi.LIBRA, "Vrischikam": Rashi.SCORPIO, "Vrischika": Rashi.SCORPIO,
    "Dhanusu": Rashi.SAGITTARIUS, "Dhanu": Rashi.SAGITTARIUS,
    "Makaram": Rashi.CAPRICORN, "Makara": Rashi.CAPRICORN,
    "Kumbam": Rashi.AQUARIUS, "Kumbha": Rashi.AQUARIUS,
    "Meenam": Rashi.PISCES, "Meena": Rashi.PISCES,
    "Vrishabha": Rashi.TAURUS, "Mithuna": Rashi.GEMINI, "Karka": Rashi.CANCER,
    "Karkata": Rashi.CANCER, "Simha": Rashi.LEO, "Tula": Rashi.LIBRA,
    "Vrishchik": Rashi.SCORPIO, "Mesh": Rashi.ARIES, "Vrishabh": Rashi.TAURUS,
    "Mithun": Rashi.GEMINI, "Kark": Rashi.CANCER, "Sinh": Rashi.LEO,
}.items():
    _RASHI_ALIASES.setdefault(_squash(_tamil), _rashi)


def resolve_rashi(name: str | int) -> Rashi:
    """Resolve a sign by id (1-12) or by name in any of the forms the API emits."""
    if isinstance(name, int) or (isinstance(name, str) and name.strip().isdigit()):
        value = int(name)
        if 1 <= value <= 12:
            return Rashi(value)
        raise NameResolutionError(f"Sign id out of range: {value}")
    key = _squash(str(name))
    if key in _RASHI_ALIASES:
        return _RASHI_ALIASES[key]
    raise NameResolutionError(f"Unrecognised sign name: {name!r}")


def try_resolve_rashi(name: str | int) -> Rashi | None:
    try:
        return resolve_rashi(name)
    except (NameResolutionError, ValueError):
        return None


def rashi_at(longitude: float) -> tuple[Rashi, float]:
    """Return (sign, degree within sign) for a sidereal longitude."""
    lon = normalise_longitude(longitude)
    return Rashi(int(lon // 30) + 1), lon % 30.0


# --- Graha ------------------------------------------------------------------------------

_GRAHA_ALIASES: dict[str, Graha] = {}
for _g in Graha:
    for _variant in (_g.value, _g.hi, _g.short_en, _g.short_hi):
        _GRAHA_ALIASES.setdefault(_squash(_variant), _g)
# Alternate Devanagari spellings and Sanskrit names the dasha / panchang endpoints return.
for _alias, _graha in {
    "चन्द्र": Graha.MOON, "चन्द्रमा": Graha.MOON, "चंद्रमा": Graha.MOON,
    "रवि": Graha.SUN, "आदित्य": Graha.SUN, "सूर्य": Graha.SUN,
    "बृहस्पति": Graha.JUPITER, "गुरू": Graha.JUPITER, "बुध": Graha.MERCURY,
    "शनैश्चर": Graha.SATURN, "शनी": Graha.SATURN,
    "Chandra": Graha.MOON, "Ravi": Graha.SUN, "Surya": Graha.SUN,
    "Budha": Graha.MERCURY, "Guru": Graha.JUPITER, "Brihaspati": Graha.JUPITER,
    "Shukra": Graha.VENUS, "Shani": Graha.SATURN, "Sani": Graha.SATURN,
    "Mangal": Graha.MARS, "Kuja": Graha.MARS, "Angaraka": Graha.MARS,
    "Sukra": Graha.VENUS, "Chandran": Graha.MOON, "Sooryan": Graha.SUN,
}.items():
    _GRAHA_ALIASES.setdefault(_squash(_alias), _graha)

_ASCENDANT_KEYS = {_squash(v) for v in ("Ascendant", "लग्न", "Lagna", "Asc", "As", "ल", "Lagnam")}


def resolve_graha(name: str) -> Graha:
    """Resolve a planet label to its canonical Graha.

    The API returns Hindi names when ``lang=hi``, so this is on the hot path for every
    Hindi report. Raises on the Ascendant — it is a point, not a graha; call
    ``is_ascendant`` first if the caller accepts either.
    """
    key = _squash(name)
    if not key:
        raise NameResolutionError("Empty planet name")
    if key in _GRAHA_ALIASES:
        return _GRAHA_ALIASES[key]
    if key in _ASCENDANT_KEYS:
        raise NameResolutionError(
            f"{name!r} is the Ascendant, not a graha — use is_ascendant() to accept it"
        )
    raise NameResolutionError(f"Unrecognised planet name: {name!r}")


def try_resolve_graha(name: str) -> Graha | None:
    try:
        return resolve_graha(name)
    except NameResolutionError:
        return None


def is_ascendant(name: str) -> bool:
    return _squash(name) in _ASCENDANT_KEYS


def graha_label(name: str, lang: str) -> str:
    """Display label for any planet-ish string, falling back to the input unchanged.

    Used where a raw API label reaches a template (e.g. a dasha lord) and must be shown in
    the report language without the caller having to branch.
    """
    if is_ascendant(name):
        return "लग्न" if lang == "hi" else ASCENDANT
    graha = try_resolve_graha(name)
    if graha is None:
        return str(name)
    return graha.hi if lang == "hi" else graha.value


def format_degree(degree: float, lang: str = "en") -> str:
    """Format a degree-within-sign as 12°34' — the form used in every table and chart.

    Devanagari digits for Hindi, because a Hindi page with Latin numerals in the tables and
    Devanagari in the prose reads as machine output.
    """
    degree = float(degree)
    whole = int(degree)
    minutes = int(round((degree - whole) * 60))
    if minutes == 60:  # 12.9999 must not render as 12°60'
        whole, minutes = whole + 1, 0
    text = f"{whole}°{minutes:02d}'"
    return to_devanagari_digits(text) if lang == "hi" else text


_DEVANAGARI_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")


def to_devanagari_digits(text: str) -> str:
    return str(text).translate(_DEVANAGARI_DIGITS)

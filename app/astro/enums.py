"""Frozen vocabulary for the astrology layer.

The point of this module is LAW 2 (the LLM never computes) and defect #2 from the spec —
Jupiter described as "exalted" in one section and "own sign" in another. Dignity, avastha
and sign are enums with a single display string per language, so a section cannot invent
its own wording: it renders ``dignity.label("hi")`` or it renders nothing.
"""
from __future__ import annotations

from enum import IntEnum, StrEnum


class Graha(StrEnum):
    """The nine grahas. Value is the canonical English name AstrologyAPI uses with lang=en."""

    SUN = "Sun"
    MOON = "Moon"
    MARS = "Mars"
    MERCURY = "Mercury"
    JUPITER = "Jupiter"
    VENUS = "Venus"
    SATURN = "Saturn"
    RAHU = "Rahu"
    KETU = "Ketu"

    @property
    def hi(self) -> str:
        return _GRAHA_HI[self]

    @property
    def short_en(self) -> str:
        return _GRAHA_SHORT_EN[self]

    @property
    def short_hi(self) -> str:
        return _GRAHA_SHORT_HI[self]

    @property
    def is_node(self) -> bool:
        """Rahu and Ketu own no sign, so dignity and Shadbala treat them separately."""
        return self in (Graha.RAHU, Graha.KETU)

    @property
    def is_natural_benefic(self) -> bool:
        """Naisargika (natural) benefic status — used for chart colouring and yoga rules.

        Mercury is conditionally benefic (it takes the character of its associations) and
        the Moon is benefic only when waxing; both are treated as benefic here and refined
        by the yoga rules that care. Nodes are neither.
        """
        return self in (Graha.JUPITER, Graha.VENUS, Graha.MERCURY, Graha.MOON)

    @property
    def is_natural_malefic(self) -> bool:
        return self in (Graha.SUN, Graha.MARS, Graha.SATURN, Graha.RAHU, Graha.KETU)


# Ascendant is not a graha — it is a point. It gets its own constant rather than a Graha
# member so `for g in Graha` never accidentally treats the Lagna as a planet.
ASCENDANT = "Ascendant"

# The seven that contribute to Ashtakavarga and carry Shadbala. Rahu/Ketu are excluded by
# classical convention: the BAV matrix is 8 rows (7 grahas + Lagna), not 10.
SAPTA_GRAHA: tuple[Graha, ...] = (
    Graha.SUN, Graha.MOON, Graha.MARS, Graha.MERCURY,
    Graha.JUPITER, Graha.VENUS, Graha.SATURN,
)

_GRAHA_HI: dict[Graha, str] = {
    Graha.SUN: "सूर्य", Graha.MOON: "चंद्र", Graha.MARS: "मंगल",
    Graha.MERCURY: "बुध", Graha.JUPITER: "गुरु", Graha.VENUS: "शुक्र",
    Graha.SATURN: "शनि", Graha.RAHU: "राहु", Graha.KETU: "केतु",
}

_GRAHA_SHORT_EN: dict[Graha, str] = {
    Graha.SUN: "Su", Graha.MOON: "Mo", Graha.MARS: "Ma", Graha.MERCURY: "Me",
    Graha.JUPITER: "Ju", Graha.VENUS: "Ve", Graha.SATURN: "Sa",
    Graha.RAHU: "Ra", Graha.KETU: "Ke",
}

_GRAHA_SHORT_HI: dict[Graha, str] = {
    Graha.SUN: "सू", Graha.MOON: "चं", Graha.MARS: "मं", Graha.MERCURY: "बु",
    Graha.JUPITER: "गु", Graha.VENUS: "शु", Graha.SATURN: "श",
    Graha.RAHU: "रा", Graha.KETU: "के",
}


class Rashi(IntEnum):
    """Zodiac signs, 1-indexed to match the API's ``sign_id``."""

    ARIES = 1
    TAURUS = 2
    GEMINI = 3
    CANCER = 4
    LEO = 5
    VIRGO = 6
    LIBRA = 7
    SCORPIO = 8
    SAGITTARIUS = 9
    CAPRICORN = 10
    AQUARIUS = 11
    PISCES = 12

    @property
    def en(self) -> str:
        return self.name.capitalize()

    @property
    def hi(self) -> str:
        return _RASHI_HI[self]

    @property
    def lord(self) -> Graha:
        return _RASHI_LORD[self]

    @property
    def element(self) -> str:
        """fire | earth | air | water — drives the Gandanta junctions and Nabhasa yogas."""
        return ("fire", "earth", "air", "water")[(self.value - 1) % 4]

    @property
    def is_odd(self) -> bool:
        """Odd (masculine) signs. Baladi avastha runs forward in these, reversed in even ones."""
        return self.value % 2 == 1

    def label(self, lang: str) -> str:
        return self.hi if lang == "hi" else self.en


_RASHI_HI: dict[Rashi, str] = {
    Rashi.ARIES: "मेष", Rashi.TAURUS: "वृषभ", Rashi.GEMINI: "मिथुन",
    Rashi.CANCER: "कर्क", Rashi.LEO: "सिंह", Rashi.VIRGO: "कन्या",
    Rashi.LIBRA: "तुला", Rashi.SCORPIO: "वृश्चिक", Rashi.SAGITTARIUS: "धनु",
    Rashi.CAPRICORN: "मकर", Rashi.AQUARIUS: "कुम्भ", Rashi.PISCES: "मीन",
}

_RASHI_LORD: dict[Rashi, Graha] = {
    Rashi.ARIES: Graha.MARS, Rashi.TAURUS: Graha.VENUS, Rashi.GEMINI: Graha.MERCURY,
    Rashi.CANCER: Graha.MOON, Rashi.LEO: Graha.SUN, Rashi.VIRGO: Graha.MERCURY,
    Rashi.LIBRA: Graha.VENUS, Rashi.SCORPIO: Graha.MARS, Rashi.SAGITTARIUS: Graha.JUPITER,
    Rashi.CAPRICORN: Graha.SATURN, Rashi.AQUARIUS: Graha.SATURN, Rashi.PISCES: Graha.JUPITER,
}


class Dignity(StrEnum):
    """Compound (Panchadha Maitri) dignity.

    Ordered strongest to weakest. The label strings are the ONLY wording any section may
    use for dignity — see the ``dignity_consistency`` gate check, which compares the word
    in the rendered HTML against ``label()`` for every planet in every section it appears.
    """

    EXALTED = "exalted"
    MOOLATRIKONA = "moolatrikona"
    OWN = "own"
    GREAT_FRIEND = "great_friend"
    FRIEND = "friend"
    NEUTRAL = "neutral"
    ENEMY = "enemy"
    GREAT_ENEMY = "great_enemy"
    DEBILITATED = "debilitated"

    @property
    def rank(self) -> int:
        """9 (exalted) down to 1 (debilitated). For sorting and strength weighting."""
        return 9 - _DIGNITY_ORDER.index(self)

    @property
    def is_strong(self) -> bool:
        return self in (Dignity.EXALTED, Dignity.MOOLATRIKONA, Dignity.OWN, Dignity.GREAT_FRIEND)

    @property
    def is_weak(self) -> bool:
        return self in (Dignity.DEBILITATED, Dignity.GREAT_ENEMY, Dignity.ENEMY)

    def label(self, lang: str) -> str:
        return (_DIGNITY_HI if lang == "hi" else _DIGNITY_EN)[self]


_DIGNITY_ORDER: tuple[Dignity, ...] = (
    Dignity.EXALTED, Dignity.MOOLATRIKONA, Dignity.OWN, Dignity.GREAT_FRIEND,
    Dignity.FRIEND, Dignity.NEUTRAL, Dignity.ENEMY, Dignity.GREAT_ENEMY,
    Dignity.DEBILITATED,
)

_DIGNITY_EN: dict[Dignity, str] = {
    Dignity.EXALTED: "exalted",
    Dignity.MOOLATRIKONA: "in its Moolatrikona",
    Dignity.OWN: "in its own sign",
    Dignity.GREAT_FRIEND: "in a great friend's sign",
    Dignity.FRIEND: "in a friend's sign",
    Dignity.NEUTRAL: "in a neutral sign",
    Dignity.ENEMY: "in an enemy's sign",
    Dignity.GREAT_ENEMY: "in a bitter enemy's sign",
    Dignity.DEBILITATED: "debilitated",
}

_DIGNITY_HI: dict[Dignity, str] = {
    Dignity.EXALTED: "उच्च",
    Dignity.MOOLATRIKONA: "मूलत्रिकोण में",
    Dignity.OWN: "स्वराशि में",
    Dignity.GREAT_FRIEND: "अधिमित्र राशि में",
    Dignity.FRIEND: "मित्र राशि में",
    Dignity.NEUTRAL: "सम राशि में",
    Dignity.ENEMY: "शत्रु राशि में",
    Dignity.GREAT_ENEMY: "अधिशत्रु राशि में",
    Dignity.DEBILITATED: "नीच",
}


class Relation(StrEnum):
    """A single cell of the Panchadha Maitri table, before it becomes a Dignity."""

    GREAT_FRIEND = "great_friend"
    FRIEND = "friend"
    NEUTRAL = "neutral"
    ENEMY = "enemy"
    GREAT_ENEMY = "great_enemy"

    def to_dignity(self) -> Dignity:
        return Dignity(self.value)


class BaladiAvastha(StrEnum):
    """Age-state by degree within the sign. Runs forward in odd signs, reversed in even."""

    BALA = "bala"
    KUMARA = "kumara"
    YUVA = "yuva"
    VRIDDHA = "vriddha"
    MRITA = "mrita"

    @property
    def strength_factor(self) -> float:
        """Classical proportion of a planet's effect that manifests in this state."""
        return {
            BaladiAvastha.BALA: 0.25,
            BaladiAvastha.KUMARA: 0.50,
            BaladiAvastha.YUVA: 1.00,
            BaladiAvastha.VRIDDHA: 0.25,
            BaladiAvastha.MRITA: 0.00,
        }[self]

    def label(self, lang: str) -> str:
        return (_BALADI_HI if lang == "hi" else _BALADI_EN)[self]


_BALADI_EN: dict[BaladiAvastha, str] = {
    BaladiAvastha.BALA: "infant (Bala)",
    BaladiAvastha.KUMARA: "adolescent (Kumara)",
    BaladiAvastha.YUVA: "youthful (Yuva)",
    BaladiAvastha.VRIDDHA: "aged (Vriddha)",
    BaladiAvastha.MRITA: "spent (Mrita)",
}

_BALADI_HI: dict[BaladiAvastha, str] = {
    BaladiAvastha.BALA: "बाल",
    BaladiAvastha.KUMARA: "कुमार",
    BaladiAvastha.YUVA: "युवा",
    BaladiAvastha.VRIDDHA: "वृद्ध",
    BaladiAvastha.MRITA: "मृत",
}


class Bhava(IntEnum):
    """Houses 1-12, with the classical groupings the yoga rules ask about."""

    H1 = 1
    H2 = 2
    H3 = 3
    H4 = 4
    H5 = 5
    H6 = 6
    H7 = 7
    H8 = 8
    H9 = 9
    H10 = 10
    H11 = 11
    H12 = 12

    @property
    def is_kendra(self) -> bool:
        """Angular / Kendra — 1, 4, 7, 10."""
        return self.value in (1, 4, 7, 10)

    @property
    def is_trikona(self) -> bool:
        """Trine / Trikona — 1, 5, 9."""
        return self.value in (1, 5, 9)

    @property
    def is_dusthana(self) -> bool:
        """Difficult houses — 6, 8, 12. A gemstone for one of these lords is banned."""
        return self.value in (6, 8, 12)

    @property
    def is_maraka_sthana(self) -> bool:
        """2 and 7 — relevant to the Vipreet and Arishta rules only. Never used for longevity."""
        return self.value in (2, 7)

    @property
    def is_upachaya(self) -> bool:
        """Growth houses — 3, 6, 10, 11. Malefics do well here."""
        return self.value in (3, 6, 10, 11)


class YogaCategory(StrEnum):
    RAJA = "raja"
    DHANA = "dhana"
    MAHAPURUSHA = "mahapurusha"
    SPIRITUAL = "spiritual"
    ARISHTA = "arishta"
    NABHASA = "nabhasa"

    def label(self, lang: str) -> str:
        return (_YOGA_CAT_HI if lang == "hi" else _YOGA_CAT_EN)[self]


_YOGA_CAT_EN: dict[YogaCategory, str] = {
    YogaCategory.RAJA: "Raja Yoga",
    YogaCategory.DHANA: "Dhana Yoga",
    YogaCategory.MAHAPURUSHA: "Panchamahapurusha Yoga",
    YogaCategory.SPIRITUAL: "Spiritual Yoga",
    YogaCategory.ARISHTA: "Arishta (Affliction)",
    YogaCategory.NABHASA: "Nabhasa Yoga",
}

_YOGA_CAT_HI: dict[YogaCategory, str] = {
    YogaCategory.RAJA: "राज योग",
    YogaCategory.DHANA: "धन योग",
    YogaCategory.MAHAPURUSHA: "पंचमहापुरुष योग",
    YogaCategory.SPIRITUAL: "आध्यात्मिक योग",
    YogaCategory.ARISHTA: "अरिष्ट",
    YogaCategory.NABHASA: "नाभस योग",
}


class Severity(StrEnum):
    """Dosha severity band. Derived from the 0-100 score, never asserted independently."""

    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    STRONG = "strong"

    @classmethod
    def from_score(cls, score: int) -> Severity:
        if score <= 0:
            return cls.NONE
        if score < 34:
            return cls.MILD
        if score < 67:
            return cls.MODERATE
        return cls.STRONG

    def label(self, lang: str) -> str:
        return (_SEVERITY_HI if lang == "hi" else _SEVERITY_EN)[self]


_SEVERITY_EN: dict[Severity, str] = {
    Severity.NONE: "not present",
    Severity.MILD: "mild",
    Severity.MODERATE: "moderate",
    Severity.STRONG: "strong",
}

_SEVERITY_HI: dict[Severity, str] = {
    Severity.NONE: "अनुपस्थित",
    Severity.MILD: "अल्प",
    Severity.MODERATE: "मध्यम",
    Severity.STRONG: "प्रबल",
}


class SadeSatiPhase(StrEnum):
    """Which third of the 7.5-year Saturn passage the native is in.

    NONE is a real answer, not a placeholder — defect #6 was rendering an em-dash here.
    """

    NONE = "none"
    RISING = "rising"
    PEAK = "peak"
    SETTING = "setting"

    def label(self, lang: str) -> str:
        return (_SADESATI_HI if lang == "hi" else _SADESATI_EN)[self]


_SADESATI_EN: dict[SadeSatiPhase, str] = {
    SadeSatiPhase.NONE: "not currently running",
    SadeSatiPhase.RISING: "first phase (Saturn in the 12th from your Moon)",
    SadeSatiPhase.PEAK: "middle phase (Saturn over your Moon)",
    SadeSatiPhase.SETTING: "final phase (Saturn in the 2nd from your Moon)",
}

_SADESATI_HI: dict[SadeSatiPhase, str] = {
    SadeSatiPhase.NONE: "इस समय सक्रिय नहीं",
    SadeSatiPhase.RISING: "प्रथम चरण (चंद्र से बारहवें शनि)",
    SadeSatiPhase.PEAK: "मध्य चरण (चंद्र राशि पर शनि)",
    SadeSatiPhase.SETTING: "अंतिम चरण (चंद्र से दूसरे शनि)",
}


class TransitGrade(StrEnum):
    """Ashtakavarga verdict on a transit — the spec's Part 2.9 filter.

    >= 4 bindus for the transiting planet in that sign is supportive, <= 2 is stressful.
    """

    SUPPORTIVE = "supportive"
    MIXED = "mixed"
    STRESSFUL = "stressful"

    @classmethod
    def from_bindus(cls, bindus: int) -> TransitGrade:
        if bindus >= 4:
            return cls.SUPPORTIVE
        if bindus <= 2:
            return cls.STRESSFUL
        return cls.MIXED

    def label(self, lang: str) -> str:
        return (_GRADE_HI if lang == "hi" else _GRADE_EN)[self]


_GRADE_EN: dict[TransitGrade, str] = {
    TransitGrade.SUPPORTIVE: "supportive",
    TransitGrade.MIXED: "mixed",
    TransitGrade.STRESSFUL: "demanding",
}

_GRADE_HI: dict[TransitGrade, str] = {
    TransitGrade.SUPPORTIVE: "अनुकूल",
    TransitGrade.MIXED: "मिश्रित",
    TransitGrade.STRESSFUL: "श्रमसाध्य",
}


# --- Ashtakavarga invariant -------------------------------------------------------------
# The Sarvashtakavarga total across all 12 signs is ALWAYS 337 for every chart ever cast.
# It is a property of the benefic-point tables, not of the native. Defect #4 was copy that
# framed it as a score out of 365 and called "above 337" strong. The only valid intra-chart
# comparison is against the mean below.
SAV_TOTAL = 337
SAV_MEAN = SAV_TOTAL / 12  # 28.0833... — houses above this are supported, below need effort
SAV_SUPPORTED_THRESHOLD = 30
SAV_EFFORT_THRESHOLD = 25

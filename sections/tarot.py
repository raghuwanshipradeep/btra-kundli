from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData

SIGN_TO_ARCANA = {
    "Aries": {"card": "The Emperor", "number": "IV", "meaning": "Authority, structure, leadership. The native has strong willpower and desire to build lasting foundations."},
    "Taurus": {"card": "The Hierophant", "number": "V", "meaning": "Tradition, wisdom, spiritual guidance. The native values stability, comfort, and time-tested truths."},
    "Gemini": {"card": "The Lovers", "number": "VI", "meaning": "Choices, duality, partnerships. The native faces key decisions and seeks harmony between opposites."},
    "Cancer": {"card": "The Chariot", "number": "VII", "meaning": "Determination, emotional courage, triumph. The native overcomes obstacles through inner strength."},
    "Leo": {"card": "Strength", "number": "VIII", "meaning": "Courage, passion, inner power. The native radiates confidence and tames challenges with grace."},
    "Virgo": {"card": "The Hermit", "number": "IX", "meaning": "Introspection, wisdom, solitude. The native seeks knowledge and truth through quiet analysis."},
    "Libra": {"card": "Justice", "number": "XI", "meaning": "Balance, fairness, karma. The native is driven by truth, harmony, and equitable outcomes."},
    "Scorpio": {"card": "Death", "number": "XIII", "meaning": "Transformation, rebirth, deep change. The native embraces endings as doorways to powerful new beginnings."},
    "Sagittarius": {"card": "Temperance", "number": "XIV", "meaning": "Balance, moderation, purpose. The native blends vision with patience for meaningful progress."},
    "Capricorn": {"card": "The Devil", "number": "XV", "meaning": "Ambition, material mastery, shadow work. The native must confront attachments to achieve true freedom."},
    "Aquarius": {"card": "The Star", "number": "XVII", "meaning": "Hope, inspiration, humanitarian vision. The native brings innovation and idealism to the world."},
    "Pisces": {"card": "The Moon", "number": "XVIII", "meaning": "Intuition, dreams, the unconscious. The native navigates life through deep emotional and psychic awareness."},
}

PLANET_ARCANA = {
    "Sun": {"card": "The Sun", "number": "XIX", "meaning": "Vitality, joy, success. Radiant energy and clarity illuminate the path."},
    "Moon": {"card": "The High Priestess", "number": "II", "meaning": "Intuition, mystery, inner wisdom. Hidden knowledge guides through subtle awareness."},
    "Mars": {"card": "The Tower", "number": "XVI", "meaning": "Sudden change, upheaval, breakthrough. Destruction clears the way for truth."},
    "Mercury": {"card": "The Magician", "number": "I", "meaning": "Skill, resourcefulness, communication. All tools are available to manifest reality."},
    "Jupiter": {"card": "Wheel of Fortune", "number": "X", "meaning": "Destiny, cycles, expansion. Life's turning points bring growth and opportunity."},
    "Venus": {"card": "The Empress", "number": "III", "meaning": "Abundance, beauty, fertility. Creative and nurturing energies flow freely."},
    "Saturn": {"card": "The World", "number": "XXI", "meaning": "Completion, mastery, fulfillment. Discipline and perseverance lead to wholeness."},
    "Rahu": {"card": "The Fool", "number": "0", "meaning": "New beginnings, unlimited potential. The journey into the unknown holds infinite possibilities."},
    "Ketu": {"card": "Judgement", "number": "XX", "meaning": "Liberation, spiritual awakening. Past karma resolves through self-realization."},
}


def render_tarot(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets or not data.astro_details:
        return None

    moon = next((p for p in data.planets if p.name == "Moon"), None)
    sun = next((p for p in data.planets if p.name == "Sun"), None)

    cards = []

    asc_sign = data.astro_details.ascendant
    if asc_sign and asc_sign in SIGN_TO_ARCANA:
        arcana = SIGN_TO_ARCANA[asc_sign]
        cards.append({
            "source": "Ascendant",
            "sign_or_planet": asc_sign,
            **arcana,
        })

    if moon and moon.sign in SIGN_TO_ARCANA:
        arcana = SIGN_TO_ARCANA[moon.sign]
        cards.append({
            "source": "Moon Sign",
            "sign_or_planet": moon.sign,
            **arcana,
        })

    if sun and sun.sign in SIGN_TO_ARCANA:
        arcana = SIGN_TO_ARCANA[sun.sign]
        cards.append({
            "source": "Sun Sign",
            "sign_or_planet": sun.sign,
            **arcana,
        })

    for p in data.planets:
        if p.name in PLANET_ARCANA and p.name != "Ascendant":
            arcana = PLANET_ARCANA[p.name]
            cards.append({
                "source": f"Planet: {p.name}",
                "sign_or_planet": p.name,
                **arcana,
            })

    if not cards:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("tarot.html")
    return template.render(
        tarot_cards=cards,
        locale=locale,
        lang=lang,
    )

from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData

OUTER_PLANETS = {
    "Uranus": {
        "deity_en": "Arun Dev",
        "deity_hi": "अरुण देव",
        "myth_en": (
            "Uranus channels the energy of Arun Dev, the celestial charioteer who "
            "drives the Sun's chariot across the sky each dawn. Just as Arun Dev "
            "heralds sudden light after darkness, Uranus brings unexpected awakenings, "
            "flashes of insight, and revolutionary change to your life."
        ),
        "myth_hi": (
            "यूरेनस अरुण देव की ऊर्जा का वाहक है — वही दिव्य सारथी जो प्रतिदिन "
            "सूर्य के रथ को अंधकार से प्रकाश की ओर ले जाते हैं। जैसे अरुण देव अचानक "
            "उजाला लाते हैं, वैसे ही यूरेनस आपके जीवन में अप्रत्याशित जागृति, अंतर्दृष्टि "
            "के चमत्कार और क्रांतिकारी परिवर्तन लाता है।"
        ),
    },
    "Neptune": {
        "deity_en": "Varun Dev",
        "deity_hi": "वरुण देव",
        "myth_en": (
            "Neptune embodies Varun Dev, the cosmic lord of waters and keeper of "
            "celestial order (Rita). Varun Dev rules the vast, mysterious ocean — "
            "both literal and metaphorical. Neptune in your chart reveals where "
            "intuition, dreams, and spiritual longing shape your deepest reality."
        ),
        "myth_hi": (
            "नेपच्यून वरुण देव का प्रतिनिधित्व करता है — वही ब्रह्मांडीय जल देवता "
            "जो दिव्य व्यवस्था (ऋत) के संरक्षक हैं। वरुण देव विशाल और रहस्यमय "
            "सागर पर राज करते हैं। आपकी कुंडली में नेपच्यून बताता है कि अंतर्ज्ञान, "
            "स्वप्न और आध्यात्मिक लालसा आपकी गहनतम वास्तविकता को कैसे आकार देते हैं।"
        ),
    },
    "Pluto": {
        "deity_en": "Yama / Shiva",
        "deity_hi": "यम / शिव",
        "myth_en": (
            "Pluto carries the transformative power of Yama, lord of death and "
            "dharma, merged with Shiva's destructive-creative aspect. Where Yama "
            "teaches that every ending carries the seed of justice and renewal, "
            "Pluto in your chart marks the arena of your deepest transformation "
            "and rebirth."
        ),
        "myth_hi": (
            "प्लूटो यम की रूपांतरकारी शक्ति का वाहक है — वही मृत्यु और धर्म के "
            "स्वामी — जो शिव के विनाश-सृजन पक्ष से मिलती है। जैसे यम सिखाते हैं "
            "कि हर अंत में न्याय और नवीनता का बीज छिपा है, वैसे ही प्लूटो आपकी "
            "कुंडली में गहनतम रूपांतरण और पुनर्जन्म का क्षेत्र दर्शाता है।"
        ),
    },
}

OUTER_PLANET_ORDER = ["Uranus", "Neptune", "Pluto"]


def render_outer_planets(data: KundliData, lang: str = "en") -> str | None:
    source = data.planets_extended or data.planets
    if not source:
        return None

    profiles = []
    for name in OUTER_PLANET_ORDER:
        planet_obj = next((p for p in source if p.name == name), None)
        if not planet_obj:
            continue

        info = OUTER_PLANETS[name]
        profiles.append({
            "name": name,
            "house": planet_obj.house,
            "sign": planet_obj.sign,
            "sign_lord": planet_obj.signLord,
            "degree": round(planet_obj.normDegree, 2),
            "nakshatra": planet_obj.nakshatra,
            "nakshatra_lord": planet_obj.nakshatraLord,
            "is_retro": str(planet_obj.isRetro).lower() in ("true", "yes", "1"),
            "deity": info[f"deity_{lang}"] if f"deity_{lang}" in info else info["deity_en"],
            "myth": info[f"myth_{lang}"] if f"myth_{lang}" in info else info["myth_en"],
            "narrative": data.narratives.get(f"outer_{name}", ""),
        })

    if not profiles:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("outer_planets.html")
    return template.render(
        profiles=profiles,
        locale=locale,
        lang=lang,
    )

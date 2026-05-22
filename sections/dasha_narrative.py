from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData

logger = logging.getLogger(__name__)

PLANET_ID_TO_NAME = {
    0: "Sun", 1: "Moon", 2: "Mars", 3: "Mercury",
    4: "Jupiter", 5: "Venus", 6: "Saturn", 7: "Rahu", 8: "Ketu",
}

NATURE_KEYWORDS: dict[str, dict[str, str]] = {
    "en": {
        "benefic_friend": "This is a highly favorable period. Both planetary energies work in harmony, supporting growth, success, and positive developments in career, relationships, and personal well-being. Opportunities arise naturally and efforts yield rewarding results.",
        "benefic_neutral": "This is a generally positive period with steady progress. While the energies are supportive, results require consistent effort. Good developments are expected in professional and personal life, though without dramatic breakthroughs.",
        "benefic_enemy": "Despite positive individual energies, an underlying tension exists between these planetary forces. Progress is possible but may come with internal conflict or mixed outcomes. Patience and careful decision-making lead to eventual success.",
        "malefic_friend": "A challenging yet growth-oriented period. The difficulties you face are purposeful — they push you toward transformation. The harmonious relationship between these planets ensures that struggles lead to meaningful lessons and eventual strength.",
        "malefic_neutral": "A period requiring caution and resilience. Obstacles and delays are likely, but they are not overwhelming. Maintain discipline, avoid risky decisions, and focus on steady progress. Health and stress management deserve attention.",
        "malefic_enemy": "This is one of the more testing periods. Conflicting energies create tension, obstacles, and potential setbacks. Patience, spiritual practice, and avoiding impulsive decisions are crucial. Remedies for both planets can help ease the impact.",
        "mixed_friend": "An interesting blend of positive and challenging energies that work together harmoniously. You may experience both gains and tests, but the overall direction is growth. Stay balanced and make the most of opportunities while managing challenges wisely.",
        "mixed_neutral": "A balanced period with ups and downs. Neither overwhelmingly positive nor negative, this time calls for steady effort and adaptability. Focus on your strengths while addressing weaknesses. Consistent work brings gradual improvement.",
        "mixed_enemy": "A complex period where progress comes with resistance. The conflicting nature of these planetary energies creates unpredictability. Stay grounded, avoid overcommitting, and focus on priorities. Strategic thinking helps navigate the mixed outcomes.",
    },
    "hi": {
        "benefic_friend": "यह एक अत्यंत अनुकूल समय है। दोनों ग्रहों की ऊर्जाएं सामंजस्य में काम करती हैं, जो करियर, रिश्तों और व्यक्तिगत कल्याण में विकास, सफलता और सकारात्मक बदलाव का समर्थन करती हैं। अवसर स्वाभाविक रूप से आते हैं और प्रयासों के फलदायी परिणाम मिलते हैं।",
        "benefic_neutral": "यह सामान्य रूप से सकारात्मक समय है जिसमें स्थिर प्रगति होती है। ऊर्जाएं सहायक हैं, लेकिन परिणामों के लिए निरंतर प्रयास की आवश्यकता होती है। पेशेवर और व्यक्तिगत जीवन में अच्छे बदलाव अपेक्षित हैं।",
        "benefic_enemy": "सकारात्मक व्यक्तिगत ऊर्जाओं के बावजूद, इन ग्रह शक्तियों के बीच एक अंतर्निहित तनाव मौजूद है। प्रगति संभव है लेकिन आंतरिक संघर्ष या मिश्रित परिणामों के साथ आ सकती है। धैर्य और सावधानीपूर्ण निर्णय अंततः सफलता की ओर ले जाते हैं।",
        "malefic_friend": "एक चुनौतीपूर्ण लेकिन विकास-उन्मुख समय। आपके सामने आने वाली कठिनाइयां उद्देश्यपूर्ण हैं — वे आपको परिवर्तन की ओर धकेलती हैं। इन ग्रहों के बीच सामंजस्यपूर्ण संबंध सुनिश्चित करता है कि संघर्ष अर्थपूर्ण सबक और अंततः शक्ति की ओर ले जाएं।",
        "malefic_neutral": "सावधानी और लचीलेपन की आवश्यकता वाला समय। बाधाएं और देरी संभव है, लेकिन वे अभिभूत करने वाली नहीं हैं। अनुशासन बनाए रखें, जोखिम भरे निर्णयों से बचें, और स्थिर प्रगति पर ध्यान दें।",
        "malefic_enemy": "यह सबसे कठिन समयों में से एक है। विरोधी ऊर्जाएं तनाव, बाधाएं और संभावित झटके पैदा करती हैं। धैर्य, आध्यात्मिक अभ्यास और आवेगी निर्णयों से बचना महत्वपूर्ण है। दोनों ग्रहों के उपाय प्रभाव को कम करने में मदद कर सकते हैं।",
        "mixed_friend": "सकारात्मक और चुनौतीपूर्ण ऊर्जाओं का एक दिलचस्प मिश्रण जो सामंजस्य में काम करता है। आप लाभ और परीक्षा दोनों अनुभव कर सकते हैं, लेकिन समग्र दिशा विकास की है।",
        "mixed_neutral": "उतार-चढ़ाव के साथ एक संतुलित समय। न अत्यधिक सकारात्मक न नकारात्मक, यह समय स्थिर प्रयास और अनुकूलनशीलता की मांग करता है। अपनी ताकत पर ध्यान दें और लगातार काम करें।",
        "mixed_enemy": "एक जटिल समय जहां प्रगति प्रतिरोध के साथ आती है। इन ग्रह ऊर्जाओं की विरोधी प्रकृति अनिश्चितता पैदा करती है। जमीन से जुड़े रहें, अत्यधिक प्रतिबद्धता से बचें, और प्राथमिकताओं पर ध्यान दें।",
    },
}


def _classify_nature(planet_name: str, planet_nature_data: list | None) -> str:
    if not planet_nature_data:
        return "mixed"
    for entry in planet_nature_data:
        if isinstance(entry, dict):
            name = entry.get("planet") or entry.get("name", "")
            if name == planet_name:
                nature = str(entry.get("nature") or entry.get("type", "")).lower()
                if "benefic" in nature or "good" in nature or "yogakaraka" in nature:
                    return "benefic"
                if "malefic" in nature or "bad" in nature or "killer" in nature:
                    return "malefic"
    return "mixed"


def _get_friendship(p1: str, p2: str, maitri_data: dict | None) -> str:
    if not maitri_data or not isinstance(maitri_data, dict):
        return "neutral"
    for planet_name, relations in maitri_data.items():
        if planet_name == p1 and isinstance(relations, dict):
            rel = str(relations.get(p2, "")).lower()
            if "friend" in rel or "mitra" in rel:
                return "friend"
            if "enemy" in rel or "shatru" in rel:
                return "enemy"
            return "neutral"
    return "neutral"


def render_dasha_narrative(data: KundliData, lang: str = "en") -> str | None:
    if not data.sub_vdasha:
        logger.debug("dasha_narrative: sub_vdasha is empty (Phase 3 sub-dasha calls may have failed)")
        return None

    keywords = NATURE_KEYWORDS.get(lang, NATURE_KEYWORDS["en"])

    current_md_planet = ""
    if data.current_vdasha and data.current_vdasha.major.planet:
        current_md_planet = data.current_vdasha.major.planet

    narratives = []
    for entry in data.sub_vdasha:
        if isinstance(entry, dict):
            ad_planet = entry.get("planet", "")
            ad_planet_id = entry.get("planet_id")
            start = entry.get("start", "")
            end = entry.get("end", "")

            if ad_planet_id is not None and not ad_planet:
                ad_planet = PLANET_ID_TO_NAME.get(ad_planet_id, "")

            if not ad_planet or not start:
                continue

            md_nature = _classify_nature(current_md_planet, data.planet_nature)
            ad_nature = _classify_nature(ad_planet, data.planet_nature)

            if md_nature == "benefic" and ad_nature == "benefic":
                combined = "benefic"
            elif md_nature == "malefic" and ad_nature == "malefic":
                combined = "malefic"
            else:
                combined = "mixed"

            friendship = _get_friendship(current_md_planet, ad_planet, data.panchada_maitri)
            narrative_key = f"{combined}_{friendship}"
            narrative = keywords.get(narrative_key, keywords.get("mixed_neutral", ""))

            md_house = ""
            ad_house = ""
            if data.planets:
                for p in data.planets:
                    if p.name == current_md_planet:
                        md_house = str(p.house)
                    if p.name == ad_planet:
                        ad_house = str(p.house)

            narratives.append({
                "md_planet": current_md_planet,
                "ad_planet": ad_planet,
                "start": start,
                "end": end,
                "md_house": md_house,
                "ad_house": ad_house,
                "md_nature": md_nature,
                "ad_nature": ad_nature,
                "friendship": friendship,
                "narrative": narrative,
            })

    if not narratives:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("dasha_narrative.html")
    return template.render(
        narratives=narratives,
        current_md_planet=current_md_planet,
        locale=locale,
        lang=lang,
    )

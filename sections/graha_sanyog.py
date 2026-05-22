from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData

CONJUNCTION_EFFECTS: dict[str, dict[str, str]] = {
    "en": {
        "Sun-Moon": "Sun-Moon conjunction brings a strong personality where mind and soul work as one. You are determined, self-aware, and emotionally driven. Leadership comes naturally but learning to separate emotion from ego is important.",
        "Sun-Mars": "Sun-Mars conjunction gives tremendous courage, energy, and ambition. You are a natural warrior with strong willpower. Success comes through bold action, but controlling anger and aggression is essential.",
        "Sun-Mercury": "Sun-Mercury conjunction (Budhaditya Yoga) sharpens intellect and communication. You have a brilliant mind with excellent analytical skills. Career success comes through knowledge, writing, or business acumen.",
        "Sun-Jupiter": "Sun-Jupiter conjunction bestows wisdom, righteousness, and spiritual inclination. You are respected for your knowledge and moral values. Government or advisory positions may bring great success.",
        "Sun-Venus": "Sun-Venus conjunction creates a charming, creative personality with love for luxury and arts. You have magnetic attraction but may face challenges in relationships due to ego clashes.",
        "Sun-Saturn": "Sun-Saturn conjunction creates tension between ambition and restriction. You face authority conflicts but develop immense discipline. Success comes late but is long-lasting through persistent hard work.",
        "Sun-Rahu": "Sun-Rahu conjunction creates an unconventional personality with intense drive for recognition. You may challenge traditional authority and carve your own unique path to power.",
        "Sun-Ketu": "Sun-Ketu conjunction brings spiritual depth and detachment from worldly ego. You have past-life wisdom but may struggle with self-confidence. Inner transformation leads to true self-realization.",
        "Moon-Mars": "Moon-Mars conjunction (Chandra-Mangal Yoga) creates emotional intensity and courage. You are passionate, protective, and action-oriented. Wealth comes through bold decisions but managing anger is key.",
        "Moon-Mercury": "Moon-Mercury conjunction gives sharp intuition combined with analytical thinking. You excel in communication, writing, and business. Emotional intelligence is your greatest asset.",
        "Moon-Jupiter": "Moon-Jupiter conjunction (Gajakesari Yoga) is highly auspicious. You are wise, generous, and emotionally balanced. Success, fame, and respect come naturally through your benevolent nature.",
        "Moon-Venus": "Moon-Venus conjunction brings artistic talent, beauty appreciation, and emotional sensitivity. You have a loving nature and attract comfort and luxury. Creativity is your strongest suit.",
        "Moon-Saturn": "Moon-Saturn conjunction creates emotional depth through challenges. You may face early hardships but develop incredible resilience. Maturity and wisdom come through life's difficult lessons.",
        "Moon-Rahu": "Moon-Rahu conjunction creates an intense, ambitious mind with unconventional thinking. You may experience anxiety but also have powerful intuition. Breaking free from mental patterns brings growth.",
        "Moon-Ketu": "Moon-Ketu conjunction brings deep spiritual sensitivity and psychic abilities. You may feel emotionally detached but possess profound inner wisdom. Meditation and spiritual practices bring peace.",
        "Mars-Mercury": "Mars-Mercury conjunction gives sharp, strategic thinking with quick decision-making. You excel in debates, engineering, and analytical fields. Channel aggression into productive intellectual pursuits.",
        "Mars-Jupiter": "Mars-Jupiter conjunction creates a righteous warrior with strong moral compass. You are brave, optimistic, and lucky. Success comes through ethical action and teaching or mentoring others.",
        "Mars-Venus": "Mars-Venus conjunction brings intense passion and creative energy. You have strong desires and artistic talent. Romantic life is eventful, and success comes through creative or entertainment fields.",
        "Mars-Saturn": "Mars-Saturn conjunction creates a disciplined warrior who achieves through sustained effort. You face obstacles that build character. Engineering, military, or construction fields bring success.",
        "Mars-Rahu": "Mars-Rahu conjunction (Angarak Yoga) creates explosive energy and unconventional ambition. You take bold risks and can achieve greatly. Controlling impulsive anger is essential for success.",
        "Mars-Ketu": "Mars-Ketu conjunction gives spiritual warrior energy with detachment from material battles. You may face sudden events but possess hidden courage. Technical or surgical skills are enhanced.",
        "Mercury-Jupiter": "Mercury-Jupiter conjunction gives excellent wisdom, knowledge, and communication skills. You are a natural teacher, advisor, or scholar. Success comes through education, law, or financial expertise.",
        "Mercury-Venus": "Mercury-Venus conjunction creates artistic intelligence and business acumen. You excel in creative writing, design, fashion, or entertainment. Social skills and charm attract success.",
        "Mercury-Saturn": "Mercury-Saturn conjunction gives methodical, deep thinking with practical wisdom. You excel in research, accounting, or technical writing. Patience in learning leads to mastery.",
        "Mercury-Rahu": "Mercury-Rahu conjunction creates an innovative, unconventional thinker. You may excel in technology, foreign languages, or breaking new intellectual ground. Guard against overthinking.",
        "Mercury-Ketu": "Mercury-Ketu conjunction brings intuitive understanding beyond logical reasoning. You may have spiritual insights and interest in occult knowledge. Mathematical or coding abilities are heightened.",
        "Jupiter-Venus": "Jupiter-Venus conjunction brings abundance, love, and spiritual wisdom. You attract wealth, beauty, and harmonious relationships. Teaching, counseling, or artistic fields bring fulfillment.",
        "Jupiter-Saturn": "Jupiter-Saturn conjunction balances expansion with discipline. You build lasting structures with wisdom. Legal, educational, or administrative careers bring steady, meaningful success.",
        "Jupiter-Rahu": "Jupiter-Rahu conjunction (Guru Chandal Yoga) challenges conventional wisdom. You question traditions and seek unconventional spiritual paths. Success comes through innovation in teaching or philosophy.",
        "Jupiter-Ketu": "Jupiter-Ketu conjunction brings profound spiritual wisdom and detachment from material gains. You are naturally inclined toward meditation, philosophy, and selfless service.",
        "Venus-Saturn": "Venus-Saturn conjunction creates mature, lasting relationships and artistic discipline. Love comes with responsibility. Success in architecture, design, or classical arts through dedicated practice.",
        "Venus-Rahu": "Venus-Rahu conjunction creates intense desires for luxury, beauty, and unconventional relationships. You may excel in glamour, entertainment, or foreign connections. Moderation brings balance.",
        "Venus-Ketu": "Venus-Ketu conjunction brings spiritual approach to love and beauty. You may experience detachment in relationships but possess refined artistic sensitivity and past-life creative talents.",
        "Saturn-Rahu": "Saturn-Rahu conjunction (Shrapit Yoga) indicates karmic lessons through hardship and delay. You face unusual challenges but develop extraordinary perseverance. Discipline overcomes obstacles.",
        "Saturn-Ketu": "Saturn-Ketu conjunction brings deep karmic purification through renunciation. You may feel isolated but develop profound inner strength. Spiritual discipline and service bring liberation.",
        "Rahu-Ketu": "Rahu-Ketu conjunction is extremely rare as they are always opposite. If computationally present, it indicates an intense karmic axis activation requiring deep spiritual transformation.",
    },
    "hi": {
        "Sun-Moon": "सूर्य-चंद्र की युति से मन और आत्मा एक साथ काम करते हैं। आप दृढ़ निश्चयी, आत्मजागरूक और भावनात्मक रूप से प्रेरित हैं। नेतृत्व स्वाभाविक रूप से आता है लेकिन भावना को अहंकार से अलग करना सीखना महत्वपूर्ण है।",
        "Sun-Mars": "सूर्य-मंगल की युति से अपार साहस, ऊर्जा और महत्वाकांक्षा मिलती है। आप एक प्राकृतिक योद्धा हैं जिनके पास मजबूत इच्छाशक्ति है। सफलता साहसिक कार्रवाई से मिलती है, लेकिन क्रोध को नियंत्रित करना आवश्यक है।",
        "Sun-Mercury": "सूर्य-बुध की युति (बुधादित्य योग) बुद्धि और संवाद को तेज करती है। आपके पास उत्कृष्ट विश्लेषणात्मक कौशल के साथ एक शानदार दिमाग है। ज्ञान, लेखन या व्यापार कौशल के माध्यम से करियर में सफलता मिलती है।",
        "Sun-Jupiter": "सूर्य-बृहस्पति की युति ज्ञान, धार्मिकता और आध्यात्मिक झुकाव प्रदान करती है। आप अपने ज्ञान और नैतिक मूल्यों के लिए सम्मानित हैं। सरकारी या सलाहकार पदों पर बड़ी सफलता मिल सकती है।",
        "Sun-Venus": "सूर्य-शुक्र की युति एक आकर्षक, रचनात्मक व्यक्तित्व बनाती है जिसमें विलासिता और कला के प्रति प्रेम होता है। आपमें चुंबकीय आकर्षण है लेकिन अहंकार के टकराव के कारण रिश्तों में चुनौतियां आ सकती हैं।",
        "Sun-Saturn": "सूर्य-शनि की युति महत्वाकांक्षा और प्रतिबंध के बीच तनाव पैदा करती है। आप अधिकार संघर्षों का सामना करते हैं लेकिन अपार अनुशासन विकसित करते हैं। सफलता देर से आती है लेकिन लंबे समय तक टिकती है।",
        "Sun-Rahu": "सूर्य-राहु की युति मान्यता के लिए तीव्र इच्छा के साथ एक अपरंपरागत व्यक्तित्व बनाती है। आप पारंपरिक अधिकार को चुनौती दे सकते हैं और सत्ता के लिए अपना अनूठा रास्ता बना सकते हैं।",
        "Sun-Ketu": "सूर्य-केतु की युति आध्यात्मिक गहराई और सांसारिक अहंकार से वैराग्य लाती है। आपके पास पूर्वजन्म की बुद्धि है लेकिन आत्मविश्वास की कमी हो सकती है। आंतरिक परिवर्तन सच्चे आत्म-साक्षात्कार की ओर ले जाता है।",
        "Moon-Mars": "चंद्र-मंगल की युति (चंद्र-मंगल योग) भावनात्मक तीव्रता और साहस पैदा करती है। आप भावुक, सुरक्षात्मक और कर्मठ हैं। साहसिक निर्णयों से धन आता है लेकिन क्रोध को प्रबंधित करना महत्वपूर्ण है।",
        "Moon-Mercury": "चंद्र-बुध की युति तीव्र अंतर्ज्ञान को विश्लेषणात्मक सोच के साथ जोड़ती है। आप संवाद, लेखन और व्यापार में उत्कृष्ट हैं। भावनात्मक बुद्धिमत्ता आपकी सबसे बड़ी संपत्ति है।",
        "Moon-Jupiter": "चंद्र-बृहस्पति की युति (गजकेसरी योग) अत्यंत शुभ है। आप बुद्धिमान, उदार और भावनात्मक रूप से संतुलित हैं। आपके परोपकारी स्वभाव के कारण सफलता, यश और सम्मान स्वाभाविक रूप से आता है।",
        "Moon-Venus": "चंद्र-शुक्र की युति कलात्मक प्रतिभा, सौंदर्य बोध और भावनात्मक संवेदनशीलता लाती है। आपमें प्यार भरा स्वभाव है और आप आराम और विलासिता आकर्षित करते हैं।",
        "Moon-Saturn": "चंद्र-शनि की युति चुनौतियों के माध्यम से भावनात्मक गहराई पैदा करती है। आपको शुरुआती कठिनाइयों का सामना करना पड़ सकता है लेकिन अविश्वसनीय लचीलापन विकसित होता है।",
        "Moon-Rahu": "चंद्र-राहु की युति अपरंपरागत सोच के साथ एक तीव्र, महत्वाकांक्षी मन बनाती है। आप चिंता अनुभव कर सकते हैं लेकिन शक्तिशाली अंतर्ज्ञान भी रखते हैं।",
        "Moon-Ketu": "चंद्र-केतु की युति गहरी आध्यात्मिक संवेदनशीलता और मानसिक क्षमताएं लाती है। आप भावनात्मक रूप से विरक्त महसूस कर सकते हैं लेकिन गहन आंतरिक ज्ञान रखते हैं।",
        "Mars-Mercury": "मंगल-बुध की युति तीव्र, रणनीतिक सोच और त्वरित निर्णय लेने की क्षमता देती है। आप बहस, इंजीनियरिंग और विश्लेषणात्मक क्षेत्रों में उत्कृष्ट हैं।",
        "Mars-Jupiter": "मंगल-बृहस्पति की युति मजबूत नैतिक दिशा के साथ एक धार्मिक योद्धा बनाती है। आप बहादुर, आशावादी और भाग्यशाली हैं। नैतिक कार्रवाई से सफलता मिलती है।",
        "Mars-Venus": "मंगल-शुक्र की युति तीव्र जुनून और रचनात्मक ऊर्जा लाती है। आपमें मजबूत इच्छाएं और कलात्मक प्रतिभा है। रचनात्मक या मनोरंजन क्षेत्रों में सफलता मिलती है।",
        "Mars-Saturn": "मंगल-शनि की युति एक अनुशासित योद्धा बनाती है जो निरंतर प्रयास से लक्ष्य प्राप्त करता है। बाधाएं चरित्र निर्माण करती हैं। इंजीनियरिंग या निर्माण क्षेत्रों में सफलता मिलती है।",
        "Mars-Rahu": "मंगल-राहु की युति (अंगारक योग) विस्फोटक ऊर्जा और अपरंपरागत महत्वाकांक्षा पैदा करती है। आप साहसिक जोखिम लेते हैं। आवेगपूर्ण क्रोध को नियंत्रित करना सफलता के लिए आवश्यक है।",
        "Mars-Ketu": "मंगल-केतु की युति भौतिक युद्धों से वैराग्य के साथ आध्यात्मिक योद्धा ऊर्जा देती है। आपमें छिपी हुई हिम्मत है। तकनीकी या शल्य कौशल बढ़ते हैं।",
        "Mercury-Jupiter": "बुध-बृहस्पति की युति उत्कृष्ट ज्ञान, विद्या और संवाद कौशल प्रदान करती है। आप एक प्राकृतिक शिक्षक या विद्वान हैं। शिक्षा, कानून या वित्तीय विशेषज्ञता से सफलता मिलती है।",
        "Mercury-Venus": "बुध-शुक्र की युति कलात्मक बुद्धिमत्ता और व्यापार कौशल बनाती है। आप रचनात्मक लेखन, डिज़ाइन या मनोरंजन में उत्कृष्ट हैं। सामाजिक कौशल और आकर्षण सफलता लाते हैं।",
        "Mercury-Saturn": "बुध-शनि की युति व्यवस्थित, गहन सोच और व्यावहारिक ज्ञान देती है। आप अनुसंधान, लेखांकन या तकनीकी लेखन में उत्कृष्ट हैं।",
        "Mercury-Rahu": "बुध-राहु की युति एक नवीन, अपरंपरागत विचारक बनाती है। आप प्रौद्योगिकी, विदेशी भाषाओं या नई बौद्धिक दिशाओं में उत्कृष्ट हो सकते हैं।",
        "Mercury-Ketu": "बुध-केतु की युति तार्किक तर्क से परे सहज समझ लाती है। आपमें आध्यात्मिक अंतर्दृष्टि और गूढ़ ज्ञान में रुचि हो सकती है। गणितीय या कोडिंग क्षमताएं बढ़ती हैं।",
        "Jupiter-Venus": "बृहस्पति-शुक्र की युति प्रचुरता, प्रेम और आध्यात्मिक ज्ञान लाती है। आप धन, सौंदर्य और सामंजस्यपूर्ण रिश्ते आकर्षित करते हैं।",
        "Jupiter-Saturn": "बृहस्पति-शनि की युति विस्तार को अनुशासन के साथ संतुलित करती है। आप ज्ञान से स्थायी संरचनाएं बनाते हैं। कानूनी, शैक्षिक या प्रशासनिक करियर में सफलता मिलती है।",
        "Jupiter-Rahu": "बृहस्पति-राहु की युति (गुरु चांडाल योग) पारंपरिक ज्ञान को चुनौती देती है। आप परंपराओं पर सवाल उठाते हैं और अपरंपरागत आध्यात्मिक मार्ग खोजते हैं।",
        "Jupiter-Ketu": "बृहस्पति-केतु की युति गहन आध्यात्मिक ज्ञान और भौतिक लाभ से वैराग्य लाती है। आप स्वाभाविक रूप से ध्यान, दर्शन और निस्वार्थ सेवा की ओर झुके हैं।",
        "Venus-Saturn": "शुक्र-शनि की युति परिपक्व, स्थायी रिश्ते और कलात्मक अनुशासन बनाती है। प्रेम जिम्मेदारी के साथ आता है। वास्तुकला या शास्त्रीय कलाओं में सफलता मिलती है।",
        "Venus-Rahu": "शुक्र-राहु की युति विलासिता, सौंदर्य और अपरंपरागत रिश्तों की तीव्र इच्छा पैदा करती है। आप ग्लैमर या विदेशी संबंधों में उत्कृष्ट हो सकते हैं। संयम संतुलन लाता है।",
        "Venus-Ketu": "शुक्र-केतु की युति प्रेम और सौंदर्य के प्रति आध्यात्मिक दृष्टिकोण लाती है। रिश्तों में वैराग्य हो सकता है लेकिन परिष्कृत कलात्मक संवेदनशीलता होती है।",
        "Saturn-Rahu": "शनि-राहु की युति (श्रापित योग) कठिनाई और विलंब के माध्यम से कर्म सबक दर्शाती है। आप असामान्य चुनौतियों का सामना करते हैं लेकिन असाधारण धैर्य विकसित करते हैं।",
        "Saturn-Ketu": "शनि-केतु की युति त्याग के माध्यम से गहन कर्म शुद्धि लाती है। आप अकेलापन महसूस कर सकते हैं लेकिन गहन आंतरिक शक्ति विकसित करते हैं।",
        "Rahu-Ketu": "राहु-केतु की युति अत्यंत दुर्लभ है क्योंकि वे हमेशा विपरीत स्थित होते हैं। यदि गणनात्मक रूप से मौजूद हो, तो यह गहन आध्यात्मिक परिवर्तन की आवश्यकता वाली तीव्र कर्म अक्ष सक्रियता को दर्शाती है।",
    },
}

PLANETS_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def _get_conjunction_key(p1: str, p2: str) -> str:
    idx1 = PLANETS_ORDER.index(p1) if p1 in PLANETS_ORDER else 99
    idx2 = PLANETS_ORDER.index(p2) if p2 in PLANETS_ORDER else 99
    if idx1 <= idx2:
        return f"{p1}-{p2}"
    return f"{p2}-{p1}"


def render_graha_sanyog(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    house_groups: dict[int, list[str]] = {}
    for p in data.planets:
        if p.name == "Ascendant":
            continue
        house_groups.setdefault(p.house, []).append(p.name)

    conjunctions = []
    effects_dict = CONJUNCTION_EFFECTS.get(lang, CONJUNCTION_EFFECTS["en"])

    for house, planets_in_house in sorted(house_groups.items()):
        if len(planets_in_house) < 2:
            continue

        planet_sign = ""
        for p in data.planets:
            if p.name == planets_in_house[0]:
                planet_sign = p.sign
                break

        pairs = []
        for i in range(len(planets_in_house)):
            for j in range(i + 1, len(planets_in_house)):
                key = _get_conjunction_key(planets_in_house[i], planets_in_house[j])
                effect = effects_dict.get(key, "")
                pairs.append({
                    "planet1": planets_in_house[i],
                    "planet2": planets_in_house[j],
                    "effect": effect,
                })

        conjunctions.append({
            "house": house,
            "sign": planet_sign,
            "planets": planets_in_house,
            "pairs": pairs,
        })

    if not conjunctions:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("graha_sanyog.html")
    return template.render(
        conjunctions=conjunctions,
        locale=locale,
        lang=lang,
    )

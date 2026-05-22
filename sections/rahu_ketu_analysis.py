from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData

AXIS_INTERPRETATIONS: dict[str, dict[str, str]] = {
    "en": {
        "1-7": "Rahu in the 1st house and Ketu in the 7th house creates a karmic pull toward self-discovery and personal identity. You are here to develop independence and a strong sense of self. Ketu in the 7th indicates past-life mastery in relationships and partnerships, but this lifetime requires you to stand on your own before truly connecting with others. You may attract unconventional partners or experience detachment in marriage until you establish your own identity first.",
        "2-8": "Rahu in the 2nd house and Ketu in the 8th house drives an intense desire for material security and wealth accumulation. You are learning to build your own resources rather than depending on inherited or shared wealth (8th house). Ketu in the 8th brings natural intuition about hidden matters and occult knowledge. Financial transformation comes through developing self-worth and independent earning capacity.",
        "3-9": "Rahu in the 3rd house and Ketu in the 9th house creates a drive to communicate, learn, and connect with the immediate environment. You are developing courage, skills, and self-expression rather than relying on higher philosophy or inherited beliefs (9th house). Ketu in the 9th indicates past-life wisdom in religion and philosophy — this life demands practical application of knowledge through media, writing, or commerce.",
        "4-10": "Rahu in the 4th house and Ketu in the 10th house creates a karmic pull toward emotional security, home, and inner peace. You seek to build a strong foundation of emotional well-being. Ketu in the 10th indicates past-life accomplishments in career and public life — this lifetime focuses on finding happiness within rather than through external achievement. Your greatest success comes when rooted in emotional stability.",
        "5-11": "Rahu in the 5th house and Ketu in the 11th house creates intense desire for creative expression, romance, and individual recognition. You are developing unique creative talents rather than following group dynamics. Ketu in the 11th indicates past-life mastery in social networks and collective goals — this lifetime asks you to trust your individual creative vision and take center stage.",
        "6-12": "Rahu in the 6th house and Ketu in the 12th house drives you to overcome challenges, serve others, and master daily discipline. You are learning to deal with practical obstacles rather than retreating into spiritual isolation (12th house). Ketu in the 12th brings natural spiritual abilities and past-life meditation experience. True liberation comes through dedicated service and overcoming earthly challenges.",
    },
    "hi": {
        "1-7": "पहले भाव में राहु और सातवें भाव में केतु आत्म-खोज और व्यक्तिगत पहचान की ओर कर्म का खिंचाव पैदा करता है। आप स्वतंत्रता और आत्मनिर्भरता विकसित करने के लिए यहां हैं। सातवें भाव में केतु पूर्वजन्म में रिश्तों में दक्षता दर्शाता है, लेकिन इस जन्म में दूसरों से जुड़ने से पहले अपनी पहचान स्थापित करना आवश्यक है।",
        "2-8": "दूसरे भाव में राहु और आठवें भाव में केतु भौतिक सुरक्षा और धन संचय की तीव्र इच्छा पैदा करता है। आप विरासत या साझा संपत्ति पर निर्भर रहने के बजाय अपने संसाधन बनाना सीख रहे हैं। आठवें भाव में केतु गूढ़ ज्ञान और छिपी बातों के बारे में प्राकृतिक अंतर्ज्ञान लाता है।",
        "3-9": "तीसरे भाव में राहु और नौवें भाव में केतु संवाद, सीखने और तत्काल वातावरण से जुड़ने की प्रेरणा देता है। आप उच्च दर्शन या विरासत में मिली मान्यताओं पर निर्भर रहने के बजाय साहस, कौशल और आत्म-अभिव्यक्ति विकसित कर रहे हैं।",
        "4-10": "चौथे भाव में राहु और दसवें भाव में केतु भावनात्मक सुरक्षा, घर और आंतरिक शांति की ओर कर्म का खिंचाव पैदा करता है। दसवें भाव में केतु पूर्वजन्म में करियर और सार्वजनिक जीवन में उपलब्धियां दर्शाता है — यह जन्म बाहरी उपलब्धि के बजाय भीतर खुशी खोजने पर केंद्रित है।",
        "5-11": "पांचवें भाव में राहु और ग्यारहवें भाव में केतु रचनात्मक अभिव्यक्ति, प्रेम और व्यक्तिगत पहचान की तीव्र इच्छा पैदा करता है। ग्यारहवें भाव में केतु पूर्वजन्म में सामाजिक नेटवर्क और सामूहिक लक्ष्यों में दक्षता दर्शाता है।",
        "6-12": "छठे भाव में राहु और बारहवें भाव में केतु चुनौतियों पर विजय, सेवा और दैनिक अनुशासन की ओर प्रेरित करता है। बारहवें भाव में केतु प्राकृतिक आध्यात्मिक क्षमताएं और पूर्वजन्म में ध्यान का अनुभव लाता है। सच्ची मुक्ति समर्पित सेवा और सांसारिक चुनौतियों पर विजय से मिलती है।",
    },
}


def _find_planet(planets: list, name: str):
    for p in planets:
        if p.name == name:
            return p
    return None


def _get_axis_key(rahu_house: int, ketu_house: int) -> str:
    pairs = [(1, 7), (2, 8), (3, 9), (4, 10), (5, 11), (6, 12)]
    for a, b in pairs:
        if (rahu_house == a and ketu_house == b) or (rahu_house == b and ketu_house == a):
            return f"{a}-{b}"
    h1, h2 = min(rahu_house, ketu_house), max(rahu_house, ketu_house)
    return f"{h1}-{h2}"


def _get_report(reports: dict | None, planet_name: str) -> str:
    if not reports:
        return ""
    entry = reports.get(planet_name, {})
    if isinstance(entry, dict):
        return entry.get("report", "")
    if isinstance(entry, str):
        return entry
    return ""


def render_rahu_ketu_analysis(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    rahu = _find_planet(data.planets, "Rahu")
    ketu = _find_planet(data.planets, "Ketu")
    if not rahu or not ketu:
        return None

    axis_key = _get_axis_key(rahu.house, ketu.house)
    axis_dict = AXIS_INTERPRETATIONS.get(lang, AXIS_INTERPRETATIONS["en"])
    axis_text = axis_dict.get(axis_key, "")

    rahu_house_report = _get_report(data.general_house_reports, "Rahu")
    rahu_rashi_report = _get_report(data.general_rashi_reports, "Rahu")
    ketu_house_report = _get_report(data.general_house_reports, "Ketu")
    ketu_rashi_report = _get_report(data.general_rashi_reports, "Ketu")

    rahu_lk_remedies = None
    ketu_lk_remedies = None
    if data.lalkitab_remedies:
        rahu_lk_remedies = data.lalkitab_remedies.get("Rahu")
        ketu_lk_remedies = data.lalkitab_remedies.get("Ketu")

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("rahu_ketu_analysis.html")
    return template.render(
        rahu=rahu,
        ketu=ketu,
        axis_key=axis_key,
        axis_text=axis_text,
        rahu_house_report=rahu_house_report,
        rahu_rashi_report=rahu_rashi_report,
        ketu_house_report=ketu_house_report,
        ketu_rashi_report=ketu_rashi_report,
        rahu_lk_remedies=rahu_lk_remedies,
        ketu_lk_remedies=ketu_lk_remedies,
        narrative=data.narratives.get("rahu_ketu_analysis", ""),
        locale=locale,
        lang=lang,
    )

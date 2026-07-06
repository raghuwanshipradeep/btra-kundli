from __future__ import annotations

PLANET_MANTRAS = {
    "Sun": {"mantra": "Om Hraam Hreem Hraum Sah Suryaya Namah", "count": 7000, "deity": "Lord Surya"},
    "Moon": {"mantra": "Om Shraam Shreem Shraum Sah Chandraya Namah", "count": 11000, "deity": "Lord Chandra"},
    "Mars": {"mantra": "Om Kraam Kreem Kraum Sah Bhaumaya Namah", "count": 10000, "deity": "Lord Hanuman"},
    "Mercury": {"mantra": "Om Braam Breem Braum Sah Budhaya Namah", "count": 9000, "deity": "Lord Vishnu"},
    "Jupiter": {"mantra": "Om Graam Greem Graum Sah Gurave Namah", "count": 19000, "deity": "Lord Brihaspati"},
    "Venus": {"mantra": "Om Draam Dreem Draum Sah Shukraya Namah", "count": 16000, "deity": "Goddess Lakshmi"},
    "Saturn": {"mantra": "Om Praam Preem Praum Sah Shanaischaraya Namah", "count": 23000, "deity": "Lord Shani"},
    "Rahu": {"mantra": "Om Bhraam Bhreem Bhraum Sah Rahave Namah", "count": 18000, "deity": "Goddess Durga"},
    "Ketu": {"mantra": "Om Sraam Sreem Sraum Sah Ketave Namah", "count": 17000, "deity": "Lord Ganesha"},
}

PLANET_MANTRAS_DEVANAGARI = {
    "Sun": "ॐ ह्रां ह्रीं ह्रौं सः सूर्याय नमः",
    "Moon": "ॐ श्रां श्रीं श्रौं सः चन्द्राय नमः",
    "Mars": "ॐ क्रां क्रीं क्रौं सः भौमाय नमः",
    "Mercury": "ॐ ब्रां ब्रीं ब्रौं सः बुधाय नमः",
    "Jupiter": "ॐ ग्रां ग्रीं ग्रौं सः गुरवे नमः",
    "Venus": "ॐ द्रां द्रीं द्रौं सः शुक्राय नमः",
    "Saturn": "ॐ प्रां प्रीं प्रौं सः शनैश्चराय नमः",
    "Rahu": "ॐ भ्रां भ्रीं भ्रौं सः राहवे नमः",
    "Ketu": "ॐ स्रां स्रीं स्रौं सः केतवे नमः",
}

PLANET_MANTRAS_MEANING = {
    "Sun": "Salutations to the Sun deity for vitality, authority, and self-confidence",
    "Moon": "Salutations to the Moon deity for emotional peace, mental clarity, and nurturing energy",
    "Mars": "Salutations to Mars for courage, physical strength, and determination",
    "Mercury": "Salutations to Mercury for intelligence, communication, and analytical ability",
    "Jupiter": "Salutations to Jupiter for wisdom, prosperity, and spiritual growth",
    "Venus": "Salutations to Venus for love, creativity, luxury, and artistic talent",
    "Saturn": "Salutations to Saturn for discipline, longevity, and karmic balance",
    "Rahu": "Salutations to Rahu for overcoming illusions and material success",
    "Ketu": "Salutations to Ketu for spiritual liberation and inner wisdom",
}

PLANET_YANTRAS = {
    "Sun": "Surya Yantra", "Moon": "Chandra Yantra", "Mars": "Mangal Yantra",
    "Mercury": "Budh Yantra", "Jupiter": "Guru Yantra", "Venus": "Shukra Yantra",
    "Saturn": "Shani Yantra", "Rahu": "Rahu Yantra", "Ketu": "Ketu Yantra",
}

PLANET_DONATIONS = {
    "Sun": {"item": "Wheat, Jaggery, Red cloth", "day": "Sunday", "metal": "Gold/Copper"},
    "Moon": {"item": "Rice, White cloth, Silver", "day": "Monday", "metal": "Silver"},
    "Mars": {"item": "Red Lentils, Red cloth, Coral", "day": "Tuesday", "metal": "Copper"},
    "Mercury": {"item": "Green Moong, Green cloth", "day": "Wednesday", "metal": "Bronze"},
    "Jupiter": {"item": "Chana Dal, Yellow cloth, Turmeric", "day": "Thursday", "metal": "Gold"},
    "Venus": {"item": "Rice, White cloth, Perfume", "day": "Friday", "metal": "Silver"},
    "Saturn": {"item": "Black Sesame, Black cloth, Iron", "day": "Saturday", "metal": "Iron"},
    "Rahu": {"item": "Black Blanket, Coconut", "day": "Saturday", "metal": "Lead"},
    "Ketu": {"item": "Blanket, Sesame, Flag", "day": "Tuesday", "metal": "Iron"},
}

BEHAVIORAL_REMEDIES = {
    "Sun": "Wake up early, offer water to Sun. Respect father and authority figures.",
    "Moon": "Meditate regularly, drink water from silver glass. Respect mother.",
    "Mars": "Practice physical exercise, avoid anger. Feed sweet food to monkeys.",
    "Mercury": "Read and study regularly, maintain cleanliness. Feed green grass to cows.",
    "Jupiter": "Respect teachers and elders, study scriptures. Feed bananas to cows.",
    "Venus": "Maintain hygiene, respect women. Donate white items on Fridays.",
    "Saturn": "Help the poor, serve elders. Feed crows on Saturdays.",
    "Rahu": "Avoid lies and deception, keep surroundings clean. Feed birds.",
    "Ketu": "Practice meditation, visit temples. Donate blankets to the needy.",
}

# Hindi translations of the donation table and behavioral remedies, used for hi PDFs
# (same planet keys as the English dicts).
PLANET_DONATIONS_HI = {
    "Sun": {"item": "गेहूं, गुड़, लाल कपड़ा", "day": "रविवार", "metal": "सोना/तांबा"},
    "Moon": {"item": "चावल, सफेद कपड़ा, चांदी", "day": "सोमवार", "metal": "चांदी"},
    "Mars": {"item": "लाल मसूर, लाल कपड़ा, मूंगा", "day": "मंगलवार", "metal": "तांबा"},
    "Mercury": {"item": "हरी मूंग, हरा कपड़ा", "day": "बुधवार", "metal": "कांसा"},
    "Jupiter": {"item": "चना दाल, पीला कपड़ा, हल्दी", "day": "गुरुवार", "metal": "सोना"},
    "Venus": {"item": "चावल, सफेद कपड़ा, इत्र", "day": "शुक्रवार", "metal": "चांदी"},
    "Saturn": {"item": "काला तिल, काला कपड़ा, लोहा", "day": "शनिवार", "metal": "लोहा"},
    "Rahu": {"item": "काला कंबल, नारियल", "day": "शनिवार", "metal": "सीसा"},
    "Ketu": {"item": "कंबल, तिल, ध्वज", "day": "मंगलवार", "metal": "लोहा"},
}

BEHAVIORAL_REMEDIES_HI = {
    "Sun": "सूर्योदय से पहले उठें, सूर्य को जल अर्पित करें। पिता और अधिकारी व्यक्तियों का सम्मान करें।",
    "Moon": "नियमित ध्यान करें, चांदी के गिलास से जल पिएं। माता का सम्मान करें।",
    "Mars": "शारीरिक व्यायाम करें, क्रोध से बचें। बंदरों को मीठा भोजन खिलाएं।",
    "Mercury": "नियमित पढ़ाई करें, स्वच्छता बनाए रखें। गायों को हरी घास खिलाएं।",
    "Jupiter": "गुरुजनों और बड़ों का सम्मान करें, शास्त्रों का अध्ययन करें। गायों को केला खिलाएं।",
    "Venus": "स्वच्छता बनाए रखें, महिलाओं का सम्मान करें। शुक्रवार को सफेद वस्तुएं दान करें।",
    "Saturn": "गरीबों की मदद करें, बुजुर्गों की सेवा करें। शनिवार को कौओं को भोजन दें।",
    "Rahu": "झूठ और छल से बचें, आसपास स्वच्छ रखें। पक्षियों को दाना खिलाएं।",
    "Ketu": "ध्यान का अभ्यास करें, मंदिर जाएं। जरूरतमंदों को कंबल दान करें।",
}

SIGN_TO_ISHTADEVATA = {
    "Aries": "Lord Hanuman", "Taurus": "Goddess Lakshmi", "Gemini": "Lord Vishnu",
    "Cancer": "Goddess Parvati", "Leo": "Lord Surya", "Virgo": "Lord Vishnu",
    "Libra": "Goddess Lakshmi", "Scorpio": "Lord Shiva", "Sagittarius": "Lord Vishnu",
    "Capricorn": "Lord Shani", "Aquarius": "Lord Shani", "Pisces": "Lord Vishnu",
}

TWELFTH_LORD_ISHTADEVATA = {
    "Sun": {"deity": "Lord Rama", "shloka": "Sri Rama Rama Rameti, Rame Raame Manorame"},
    "Moon": {"deity": "Goddess Parvati", "shloka": "Om Aim Hreem Shreem Shivayai Namah"},
    "Mars": {"deity": "Lord Hanuman", "shloka": "Om Hanumate Namah"},
    "Mercury": {"deity": "Lord Vishnu", "shloka": "Om Namo Bhagavate Vasudevaya"},
    "Jupiter": {"deity": "Lord Shiva", "shloka": "Om Namah Shivaya"},
    "Venus": {"deity": "Goddess Lakshmi", "shloka": "Om Shreem Mahalakshmiyei Namah"},
    "Saturn": {"deity": "Lord Vishnu", "shloka": "Om Namo Narayanaya"},
    "Rahu": {"deity": "Goddess Durga", "shloka": "Om Dum Durgayei Namah"},
    "Ketu": {"deity": "Lord Ganesha", "shloka": "Om Gam Ganapataye Namah"},
}

PLANET_TO_GEMSTONE = {
    "Sun": {"name": "Ruby", "hindi": "माणिक्य"},
    "Moon": {"name": "Pearl", "hindi": "मोती"},
    "Mars": {"name": "Red Coral", "hindi": "मूंगा"},
    "Mercury": {"name": "Emerald", "hindi": "पन्ना"},
    "Jupiter": {"name": "Yellow Sapphire", "hindi": "पुखराज"},
    "Venus": {"name": "Diamond", "hindi": "हीरा"},
    "Saturn": {"name": "Blue Sapphire", "hindi": "नीलम"},
    "Rahu": {"name": "Hessonite (Gomed)", "hindi": "गोमेद"},
    "Ketu": {"name": "Cat's Eye (Lehsuniya)", "hindi": "लहसुनिया"},
}

RUDRAKSHA_MEANINGS = {
    1: {"deity": "Lord Shiva", "benefit": "Spiritual growth, leadership, confidence", "planet": "Sun"},
    2: {"deity": "Ardhanarishwara", "benefit": "Harmony, relationships, emotional balance", "planet": "Moon"},
    3: {"deity": "Agni (Fire)", "benefit": "Self-confidence, energy, overcoming lethargy", "planet": "Mars"},
    4: {"deity": "Lord Brahma", "benefit": "Intelligence, communication, creativity", "planet": "Mercury"},
    5: {"deity": "Kalagni Rudra", "benefit": "Knowledge, peace, health", "planet": "Jupiter"},
    6: {"deity": "Kartikeya", "benefit": "Willpower, focus, grounding", "planet": "Venus"},
    7: {"deity": "Goddess Lakshmi", "benefit": "Wealth, prosperity, good fortune", "planet": "Saturn"},
    8: {"deity": "Lord Ganesha", "benefit": "Removal of obstacles, success", "planet": "Rahu"},
    9: {"deity": "Goddess Durga", "benefit": "Fearlessness, protection, strength", "planet": "Ketu"},
    10: {"deity": "Lord Vishnu", "benefit": "Protection, peace, pacifying all planets", "planet": "All"},
    11: {"deity": "Lord Hanuman", "benefit": "Courage, adventure, protection", "planet": "All"},
    12: {"deity": "Lord Surya", "benefit": "Radiance, authority, leadership", "planet": "Sun"},
    13: {"deity": "Lord Kamadeva", "benefit": "Charisma, attraction, fulfillment", "planet": "Venus"},
    14: {"deity": "Lord Shiva (Deva Mani)", "benefit": "Intuition, divine guidance, third eye", "planet": "Saturn"},
}

YANTRA_DOS = [
    "Place the yantra on a clean, elevated surface facing east or north",
    "Energize with mantra recitation on the planet's day",
    "Clean with rose water or Ganga Jal weekly",
    "Light a ghee lamp near the yantra during prayer",
    "Keep the yantra in your prayer room or workspace",
]

YANTRA_DONTS = [
    "Never place the yantra on the floor or in a bathroom",
    "Do not let others touch your personal yantra",
    "Avoid placing it near shoes, dustbin, or unclean areas",
    "Do not keep a damaged or cracked yantra — immerse it in flowing water",
    "Never disrespect or step over the yantra",
]

# Hindi versions for hi PDFs (same order / planet keys as the English versions).
PLANET_YANTRAS_HI = {
    "Sun": "सूर्य यंत्र", "Moon": "चंद्र यंत्र", "Mars": "मंगल यंत्र",
    "Mercury": "बुध यंत्र", "Jupiter": "गुरु यंत्र", "Venus": "शुक्र यंत्र",
    "Saturn": "शनि यंत्र", "Rahu": "राहु यंत्र", "Ketu": "केतु यंत्र",
}

YANTRA_DOS_HI = [
    "यंत्र को स्वच्छ, ऊंचे स्थान पर पूर्व या उत्तर दिशा की ओर रखें",
    "ग्रह के दिन मंत्र जाप से यंत्र को ऊर्जावान करें",
    "साप्ताहिक रूप से गुलाब जल या गंगाजल से साफ करें",
    "पूजा के समय यंत्र के पास घी का दीपक जलाएं",
    "यंत्र को अपने पूजा कक्ष या कार्यस्थल पर रखें",
]

YANTRA_DONTS_HI = [
    "यंत्र को कभी फर्श पर या बाथरूम में न रखें",
    "अपने व्यक्तिगत यंत्र को दूसरों को छूने न दें",
    "इसे जूते, कूड़ेदान या अशुद्ध स्थानों के पास रखने से बचें",
    "क्षतिग्रस्त या टूटे यंत्र को न रखें — इसे बहते जल में प्रवाहित करें",
    "यंत्र का कभी अनादर न करें या उसके ऊपर से न लांघें",
]

SIGN_LORDS: dict[str, str] = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

# ===== Hindi localization maps (for hi PDFs) =====

# Deity names shown across rudraksha / ishta-devata / mantra sections.
DEITY_HI: dict[str, str] = {
    "Lord Shiva": "भगवान शिव",
    "Lord Shiva (Deva Mani)": "भगवान शिव (देव मणि)",
    "Lord Vishnu": "भगवान विष्णु",
    "Lord Surya": "भगवान सूर्य",
    "Lord Chandra": "भगवान चंद्र",
    "Lord Hanuman": "भगवान हनुमान",
    "Lord Brihaspati": "भगवान बृहस्पति",
    "Lord Shani": "भगवान शनि",
    "Lord Ganesha": "भगवान गणेश",
    "Lord Rama": "भगवान राम",
    "Lord Brahma": "भगवान ब्रह्मा",
    "Lord Kartikeya": "भगवान कार्तिकेय",
    "Kartikeya": "भगवान कार्तिकेय",
    "Lord Kamadeva": "भगवान कामदेव",
    "Goddess Lakshmi": "देवी लक्ष्मी",
    "Goddess Durga": "देवी दुर्गा",
    "Goddess Parvati": "देवी पार्वती",
    "Ardhanarishwara": "अर्धनारीश्वर",
    "Agni (Fire)": "अग्नि देव",
    "Kalagni Rudra": "कालाग्नि रुद्र",
}

# Ishta-devata / mantra shlokas — romanized Sanskrit -> Devanagari.
SHLOKA_HI: dict[str, str] = {
    "Sri Rama Rama Rameti, Rame Raame Manorame": "श्री राम राम रामेति, रमे रामे मनोरमे",
    "Om Aim Hreem Shreem Shivayai Namah": "ॐ ऐं ह्रीं श्रीं शिवायै नमः",
    "Om Hanumate Namah": "ॐ हनुमते नमः",
    "Om Namo Bhagavate Vasudevaya": "ॐ नमो भगवते वासुदेवाय",
    "Om Namah Shivaya": "ॐ नमः शिवाय",
    "Om Shreem Mahalakshmiyei Namah": "ॐ श्रीं महालक्ष्म्यै नमः",
    "Om Namo Narayanaya": "ॐ नमो नारायणाय",
    "Om Dum Durgayei Namah": "ॐ दुं दुर्गायै नमः",
    "Om Gam Ganapataye Namah": "ॐ गं गणपतये नमः",
}

# Rudraksha benefits by mukhi (matches RUDRAKSHA_MEANINGS above).
RUDRAKSHA_BENEFIT_HI: dict[int, str] = {
    1: "आध्यात्मिक विकास, नेतृत्व, आत्मविश्वास",
    2: "सामंजस्य, रिश्ते, भावनात्मक संतुलन",
    3: "आत्मविश्वास, ऊर्जा, आलस्य पर विजय",
    4: "बुद्धि, संचार, रचनात्मकता",
    5: "ज्ञान, शांति, स्वास्थ्य",
    6: "इच्छाशक्ति, एकाग्रता, स्थिरता",
    7: "धन, समृद्धि, सौभाग्य",
    8: "बाधाओं का निवारण, सफलता",
    9: "निर्भयता, सुरक्षा, शक्ति",
    10: "सुरक्षा, शांति, सभी ग्रहों का शमन",
    11: "साहस, रोमांच, सुरक्षा",
    12: "तेज, अधिकार, नेतृत्व",
    13: "आकर्षण, सम्मोहन, पूर्णता",
    14: "अंतर्ज्ञान, दिव्य मार्गदर्शन, तीसरा नेत्र",
}

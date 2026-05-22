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

SIGN_LORDS: dict[str, str] = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Mars", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}

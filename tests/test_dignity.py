from sections.dignity import _get_dignity


def test_sun_exalted_in_aries():
    assert _get_dignity("Sun", "Aries") == "Exalted"


def test_sun_debilitated_in_libra():
    assert _get_dignity("Sun", "Libra") == "Debilitated"


def test_sun_moolatrikona_in_leo():
    assert _get_dignity("Sun", "Leo") == "Moolatrikona"


def test_sun_normal_in_scorpio():
    assert _get_dignity("Sun", "Scorpio") == "Normal"


def test_jupiter_exalted_in_cancer():
    assert _get_dignity("Jupiter", "Cancer") == "Exalted"


def test_jupiter_own_sign_pisces():
    assert _get_dignity("Jupiter", "Pisces") == "Own Sign"


def test_jupiter_moolatrikona_sagittarius():
    assert _get_dignity("Jupiter", "Sagittarius") == "Moolatrikona"


def test_saturn_debilitated_in_aries():
    assert _get_dignity("Saturn", "Aries") == "Debilitated"


# Aquarius is both Moolatrikona AND Own Sign for Saturn;
# _get_dignity returns Moolatrikona first (correct precedence).
def test_saturn_moolatrikona_aquarius():
    assert _get_dignity("Saturn", "Aquarius") == "Moolatrikona"


def test_saturn_own_sign_capricorn():
    assert _get_dignity("Saturn", "Capricorn") == "Own Sign"


def test_mars_own_sign_scorpio():
    assert _get_dignity("Mars", "Scorpio") == "Own Sign"


def test_rahu_exalted_taurus():
    assert _get_dignity("Rahu", "Taurus") == "Exalted"


def test_unknown_planet_normal():
    assert _get_dignity("Pluto", "Aries") == "Normal"

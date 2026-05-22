from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData

CHALDEAN_VALUES = {
    'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 8, 'G': 3, 'H': 5,
    'I': 1, 'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5, 'O': 7, 'P': 8,
    'Q': 1, 'R': 2, 'S': 3, 'T': 4, 'U': 6, 'V': 6, 'W': 6, 'X': 5,
    'Y': 1, 'Z': 7,
}


def _reduce_to_single_digit(n: int) -> int:
    while n > 9:
        n = sum(int(d) for d in str(abs(n)))
    return n


def chaldean_name_number(name: str) -> int:
    total = sum(CHALDEAN_VALUES.get(c.upper(), 0) for c in name if c.isalpha())
    return _reduce_to_single_digit(total) if total > 0 else 1


def connection_number(day: int, month: int) -> int:
    return _reduce_to_single_digit(day + month)


def render_numerology_personality(data: KundliData, lang: str = "en") -> str | None:
    if not data.numero_table or not isinstance(data.numero_table, dict):
        return None

    locale = LOCALES.get(lang, LOCALES["en"])

    radical = data.numero_table.get("radical_number")
    destiny = data.numero_table.get("destiny_number")
    success = chaldean_name_number(data.request.name)
    conn = connection_number(data.request.day, data.request.month)

    if radical is None and destiny is None:
        return None

    numbers = []
    if radical is not None:
        numbers.append({
            "key": "moolank",
            "label": locale.get("np_moolank", "Moolank"),
            "desc": locale.get("np_moolank_desc", ""),
            "value": radical,
            "narr_key": "numero_personality_moolank",
            "color": "#D4AF37",
        })
    if destiny is not None:
        numbers.append({
            "key": "bhagyank",
            "label": locale.get("np_bhagyank", "Bhagyank"),
            "desc": locale.get("np_bhagyank_desc", ""),
            "value": destiny,
            "narr_key": "numero_personality_bhagyank",
            "color": "#1565C0",
        })
    numbers.append({
        "key": "success",
        "label": locale.get("np_success", "Success Number"),
        "desc": locale.get("np_success_desc", ""),
        "value": success,
        "narr_key": "numero_personality_success",
        "color": "#2E7D32",
    })
    numbers.append({
        "key": "connection",
        "label": locale.get("np_connection", "Connection Number"),
        "desc": locale.get("np_connection_desc", ""),
        "value": conn,
        "narr_key": "numero_personality_connection",
        "color": "#6A1B9A",
    })

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("numerology_personality.html")
    return template.render(
        numbers=numbers,
        narratives=data.narratives,
        locale=locale,
        lang=lang,
    )

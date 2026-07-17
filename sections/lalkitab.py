from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_lalkitab(data: KundliData, lang: str = "en") -> str | None:
    if (
        not data.lalkitab_houses
        and not data.lalkitab_debts
        and not data.lalkitab_remedies
    ):
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("lalkitab.html")
    return template.render(
        houses=data.lalkitab_houses,
        debts=data.lalkitab_debts,
        remedies=data.lalkitab_remedies,
        locale=locale,
        lang=lang,
    )

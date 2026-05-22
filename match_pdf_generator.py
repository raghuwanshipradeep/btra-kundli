from __future__ import annotations

import logging
import pathlib

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from models import MatchData
from sections.matching import render_matching

logger = logging.getLogger(__name__)

TEMPLATES_DIR = pathlib.Path(__file__).parent / "templates"


class MatchPDFGenerator:
    def __init__(self) -> None:
        self._env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
        self._base_template = self._env.get_template("base.html")
        self._css = (TEMPLATES_DIR / "styles.css").read_text(encoding="utf-8")

    def generate(self, data: MatchData, lang: str = "en") -> bytes:
        sections: list[str] = []
        try:
            html = render_matching(data, lang)
            if html:
                sections.append(html)
                logger.info("Match section rendered")
        except Exception:
            logger.exception("Match section failed")

        full_html = self._base_template.render(
            sections=sections,
            lang=lang,
            css=self._css,
        )

        base_url = TEMPLATES_DIR.as_uri() + "/"
        pdf_bytes: bytes = HTML(string=full_html, base_url=base_url).write_pdf()
        logger.info("Match PDF generated: %d bytes", len(pdf_bytes))
        return pdf_bytes

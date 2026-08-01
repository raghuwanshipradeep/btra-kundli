from __future__ import annotations

import logging
import pathlib

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from config import settings
from models import KundliData
from sections import _format_degree, _safe_time, humanize_key, to_hindi_value

# Sections the "lite" tier drops. Most of the original list (tatkalik_maitri,
# bhinnashtak, char_dasha, yogini_dasha) has since been removed from the report
# outright, so lite and detailed now differ by a single section.
LITE_SKIP_SECTIONS = {
    "panchada_maitri",
}

# Image-only section pages dropped when settings.pdf_images_enabled is false.
# "front_page" is deliberately absent — the opening image always stays.
IMAGE_ONLY_SECTIONS = {
    "astrologer_intro", "divider_ganesha", "divider_grah", "divider_dosha",
    "offer_banner", "divider_numerology", "divider_lalkitab",
}
from sections.ashtakvarga import render_ashtakvarga
from sections.astro_details import render_astro_details
from sections.cover import render_cover
from sections.dasha import render_dasha
from sections.divisional_charts import render_divisional_charts
from sections.dosha import render_dosha
from sections.life_reports import render_life_reports
from sections.panchada_maitri import render_panchada_maitri
from sections.panchang import render_panchang
from sections.planet_nature import render_planet_nature
from sections.planets import render_planets
from sections.remedy_rudraksha import render_remedy_rudraksha
from sections.remedy_gemstones import render_remedy_gemstones
from sections.remedy_mantras import render_remedy_mantras
from sections.remedy_yantra import render_remedy_yantra
from sections.remedy_daan import render_remedy_daan
from sections.varshaphal import render_varshaphal
from sections.numerology import render_numerology
from sections.lalkitab import render_lalkitab
from sections.yogas import render_yogas
from sections.thematic_reports import render_thematic_reports
from sections.north_chart import render_north_chart
from sections.marriage_timing import render_marriage_timing
from sections.front_matter import render_front_matter, render_front_matter_toc
from sections.graha_profile import render_graha_profile
from sections.authors_note import render_authors_note
from sections.closing_cta import render_closing_cta
from sections.dasha_narrative import render_dasha_narrative
from sections.career_path import render_career_path
from sections.material_comforts import render_material_comforts
from sections.sadhesati_enhanced import render_sadhesati_enhanced
from sections.three_pillars import render_three_pillars
from sections.sade_sati_journey import render_sade_sati_journey
from sections.mahadasha_journey import render_mahadasha_journey
from sections.numerology_personality import render_numerology_personality
from sections.divider_images import make_divider_renderer, make_link_banner_renderer

logger = logging.getLogger(__name__)

TEMPLATES_DIR = pathlib.Path(__file__).parent / "templates"

# Promotional filler images, rotated across sparse pages and capped at
# settings.filler_max_images placements per report.
_FILLER_IMAGES = [
    str(TEMPLATES_DIR / "images" / "btr_image.JPG"),
]
# Content below this fraction of page height is the footer / page-number band and
# is ignored when measuring how far down real content reaches.
_FILLER_FOOTER_ZONE = 0.90
# Minimum pages between two filler placements. Without this the capped run lands on
# the first few consecutive sparse pages and the same image repeats back-to-back.
_FILLER_MIN_PAGE_GAP = 12


def _fill_gap_pages(pdf_bytes: bytes) -> bytes:
    """Overlay a promotional image into the empty bottom band of any page (after
    settings.filler_skip_pages) whose bottom gap exceeds settings.filler_gap_threshold,
    stopping after settings.filler_max_images placements.
    Same-page overlay only (page count unchanged). Best-effort: never raises."""
    import fitz  # PyMuPDF

    paths = [p for p in _FILLER_IMAGES if pathlib.Path(p).exists()]
    if not paths:
        logger.warning("Filler images missing; skipping gap-fill pass")
        return pdf_bytes

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    rotate = 0
    added = 0
    last_pno = -_FILLER_MIN_PAGE_GAP
    for pno in range(len(doc)):
        if added >= settings.filler_max_images:
            break
        if pno < settings.filler_skip_pages:
            continue
        if pno - last_pno < _FILLER_MIN_PAGE_GAP:
            continue
        page = doc[pno]
        H = page.rect.height
        W = page.rect.width
        cut = _FILLER_FOOTER_ZONE * H  # ignore footer/page-number band

        bottom = 0.0
        for b in page.get_text("blocks"):  # (x0, y0, x1, y1, text, block_no, block_type)
            if b[1] < cut:
                bottom = max(bottom, min(b[3], cut))
        for im in page.get_image_info():   # raster image placements
            x0, y0, x1, y1 = im["bbox"]
            # Skip near-full-page background images (they cover the whole page and
            # would mask a genuinely sparse content area).
            if (x1 - x0) > 0.85 * W and (y1 - y0) > 0.85 * H:
                continue
            if y0 < cut:
                bottom = max(bottom, min(y1, cut))

        if bottom <= 0:
            continue  # blank / vector-only page → leave alone
        if (H - bottom) / H <= settings.filler_gap_threshold:
            continue  # not enough bottom gap

        path = paths[rotate % len(paths)]
        rotate += 1
        margin = 36.0
        avail_w = W - 2 * margin
        avail_h = (cut - bottom) - 2 * margin
        if avail_w <= 0 or avail_h <= 0:
            continue
        pix = fitz.Pixmap(path)
        iw, ih = pix.width, pix.height
        if iw <= 0 or ih <= 0:
            continue
        scale = min(avail_w / iw, avail_h / ih)
        dw, dh = iw * scale, ih * scale
        x = (W - dw) / 2
        y = bottom + ((cut - bottom) - dh) / 2
        page.insert_image(fitz.Rect(x, y, x + dw, y + dh), filename=path)
        added += 1
        last_pno = pno

    if added:
        pdf_bytes = doc.tobytes()
        logger.info("Filler-image pass: added %d image(s) to sparse pages", added)
    doc.close()
    return pdf_bytes

SECTION_RENDERERS = [
    ("front_page", make_divider_renderer("front_page.png")),
    ("astrologer_intro", make_divider_renderer("astrologer.png")),
    ("authors_note", render_authors_note),
    ("front_matter", render_front_matter),          # disclaimer + how-to-read
    ("cover", render_cover),                         # personalized कुंडली रिपोर्ट cover
    ("front_matter_toc", render_front_matter_toc),   # table of contents
    ("divider_ganesha", make_divider_renderer("loard-ganesha.png")),
    ("astro_details", render_astro_details),
    ("panchang", render_panchang),
    ("dasha", render_dasha),
    ("mahadasha_journey", render_mahadasha_journey),
    ("divisional_charts", render_divisional_charts),
    ("life_reports", render_life_reports),
    ("three_pillars", render_three_pillars),
    ("divider_grah", make_divider_renderer("ghrah.png")),
    ("graha_profile", render_graha_profile),
    ("divider_dosha", make_divider_renderer("kundli-dosha.png")),
    ("dosha", render_dosha),
    ("remedy_rudraksha", render_remedy_rudraksha),
    ("remedy_gemstones", render_remedy_gemstones),
    ("remedy_mantras", render_remedy_mantras),
    ("offer_banner", make_link_banner_renderer("Artboard_offer.png", "https://gemsguruji.com/")),
    ("remedy_yantra", render_remedy_yantra),
    ("remedy_daan", render_remedy_daan),
    ("varshaphal", render_varshaphal),
    ("planets", render_planets),
    ("planet_nature", render_planet_nature),
    ("panchada_maitri", render_panchada_maitri),
    ("ashtakvarga", render_ashtakvarga),
    ("divider_numerology", make_divider_renderer("numrology.png")),
    ("numerology", render_numerology),
    ("numerology_personality", render_numerology_personality),
    ("divider_lalkitab", make_divider_renderer("lal_kitab.png")),
    ("lalkitab", render_lalkitab),
    ("yogas", render_yogas),
    ("thematic_reports", render_thematic_reports),
    ("career_path", render_career_path),
    ("marriage_timing", render_marriage_timing),
    ("material_comforts", render_material_comforts),
    ("sade_sati_journey", render_sade_sati_journey),
    ("closing_cta", render_closing_cta),
]


class PDFGenerator:
    def __init__(self) -> None:
        self._env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
        self._env.filters["safe_time"] = _safe_time
        self._env.filters["humanize_key"] = humanize_key
        self._env.filters["to_hindi_value"] = to_hindi_value
        self._env.filters["format_degree"] = _format_degree
        # Templates gate their <img> tags on these; see settings.pdf_images_enabled
        # (section artwork) and settings.pdf_logo_enabled (the brand signature).
        self._env.globals["show_images"] = settings.pdf_images_enabled
        self._env.globals["show_logo"] = settings.pdf_logo_enabled
        self._base_template = self._env.get_template("base.html")
        self._css = (TEMPLATES_DIR / "styles.css").read_text(encoding="utf-8")

    def generate(
        self,
        data: KundliData,
        lang: str = "en",
        include_sections: list[str] | None = None,
        report_tier: str = "detailed",
    ) -> bytes:
        sections: list[str] = []
        for name, renderer in SECTION_RENDERERS:
            if include_sections and name not in include_sections:
                continue
            if report_tier == "lite" and name in LITE_SKIP_SECTIONS:
                continue
            if not settings.pdf_images_enabled and name in IMAGE_ONLY_SECTIONS:
                continue
            try:
                html = renderer(data, lang)
                if html:
                    sections.append(html)
                    logger.info("Section '%s' rendered", name)
                else:
                    logger.info("Section '%s' skipped (no data)", name)
            except Exception:
                logger.exception("Section '%s' failed", name)

        brand_footer = None
        if settings.brand_footer_enabled:
            brand_footer = {
                "enabled": True,
                "name": settings.brand_footer_name,
                "url": settings.brand_footer_url,
                "phone": settings.brand_footer_phone,
            }

        full_html = self._base_template.render(
            sections=sections,
            lang=lang,
            css=self._css,
            brand_footer=brand_footer,
        )

        base_url = TEMPLATES_DIR.as_uri() + "/"
        pdf_bytes: bytes = HTML(string=full_html, base_url=base_url).write_pdf()
        logger.info("PDF generated: %d bytes, %d sections", len(pdf_bytes), len(sections))

        if settings.filler_images_enabled:
            try:
                pdf_bytes = _fill_gap_pages(pdf_bytes)
            except Exception:
                logger.exception("Filler-image pass failed; using PDF without fillers")

        return pdf_bytes

"""Per-request brand resolution.

The report can be emitted under either of two brands, chosen per request via
KundliRequest.kundli_type. Structure, sections and flow are identical; only the
surfaces below differ: the front page image, the brand logo, the page footer
(name / url / phone), the Author's Note gate, the CTA links, and the promo filler.

Why a resolved profile rather than reading `settings` at each site:

  * PDFGenerator is a module-level singleton (pipeline.py, main.py) whose generate()
    runs in asyncio.to_thread with several renders in flight at once. Per-request
    branding therefore must never mutate shared state -- not settings, not the
    Jinja env globals. A frozen profile passed around as a local is safe by
    construction.
  * Attributes are read off `settings` at call time (not at import), so tests can
    monkeypatch individual settings the way the rest of the suite already does.

get_brand() never raises: anything unrecognised falls back to Batraa. An unknown
value must not be able to fail a render -- sheet_worker parks mapping failures as
permanent, so a brand typo could otherwise strand a paid order.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from config import settings

BATRAA = "batraa"
BLOOMX = "bloomx"

# Pages that belong to Batraa alone and must not appear under another brand:
# a Batraa astrologer photo, and a banner linking to a third-party store.
# Skipped by PDFGenerator.generate() for any non-Batraa brand.
BATRAA_ONLY_SECTIONS = {"astrologer_intro", "offer_banner"}


@dataclass(frozen=True)
class Brand:
    key: str
    front_page_image: str
    logo_image: str
    logo_alt: str
    author_name: str
    author_title: str
    cta_consult_url: str
    cta_pooja_url: str
    cta_rudraksha_url: str
    footer_enabled: bool
    footer_name: str
    footer_url: str
    footer_phone: str
    # Promo images stamped onto sparse pages by _fill_gap_pages(). Empty means the
    # filler pass is skipped entirely for this brand -- Bloomx ships no promo art.
    filler_images: tuple[str, ...] = field(default=())

    @property
    def is_batraa(self) -> bool:
        return self.key == BATRAA


def _batraa() -> Brand:
    return Brand(
        key=BATRAA,
        front_page_image="front_page.jpg",
        logo_image="kundli_logo.png",
        logo_alt="The Batraa Numerology — Your Personalized Kundli Report",
        author_name=settings.author_name,
        author_title=settings.author_title,
        cta_consult_url=settings.cta_consult_url,
        cta_pooja_url=settings.cta_pooja_url,
        cta_rudraksha_url=settings.cta_rudraksha_url,
        footer_enabled=settings.brand_footer_enabled,
        footer_name=settings.brand_footer_name,
        footer_url=settings.brand_footer_url,
        footer_phone=settings.brand_footer_phone,
        filler_images=("btr_image.JPG",),
    )


def _bloomx() -> Brand:
    return Brand(
        key=BLOOMX,
        front_page_image=settings.bloomx_cover_image,
        logo_image=settings.bloomx_logo_image,
        logo_alt="The Bloomx Solutions — Your Personalized Kundli Report",
        author_name=settings.bloomx_author_name,
        author_title=settings.bloomx_author_title,
        cta_consult_url=settings.bloomx_cta_consult_url,
        cta_pooja_url=settings.bloomx_cta_pooja_url,
        cta_rudraksha_url=settings.bloomx_cta_rudraksha_url,
        footer_enabled=settings.bloomx_brand_footer_enabled,
        footer_name=settings.bloomx_brand_footer_name,
        footer_url=settings.bloomx_brand_footer_url,
        footer_phone=settings.bloomx_brand_footer_phone,
        filler_images=(),
    )


_BUILDERS = {BATRAA: _batraa, BLOOMX: _bloomx}


def get_brand(kundli_type: str | None = None) -> Brand:
    """Resolve a brand profile. Blank/unknown/None -> Batraa. Never raises."""
    key = (kundli_type or "").strip().lower()
    return _BUILDERS.get(key, _batraa)()


def brand_for(data) -> Brand:
    """Resolve the brand for a KundliData, tolerating incomplete test doubles."""
    return get_brand(getattr(getattr(data, "request", None), "kundli_type", None))

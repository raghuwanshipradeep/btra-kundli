from __future__ import annotations

from typing import TYPE_CHECKING


from branding import brand_for
from sections import make_env

if TYPE_CHECKING:
    from models import KundliData


def render_front_page(data: "KundliData", lang: str = "en") -> str | None:
    """The opening full-page image, which differs per brand.

    Unlike the other dividers this cannot be a make_divider_renderer() closure: those
    bake the filename in at import time, and the front page has to follow
    data.request.kundli_type. Keeps the (data, lang) renderer contract.
    """
    brand = brand_for(data)
    template = make_env(brand).get_template("divider_image.html")
    return template.render(image=brand.front_page_image)


def make_divider_renderer(image_filename: str):
    """Return a section renderer that emits a full-page A4 image divider."""
    def render(data: "KundliData", lang: str = "en") -> str | None:
        template = make_env().get_template("divider_image.html")
        return template.render(image=image_filename)

    render.__name__ = "render_divider_" + image_filename.rsplit(".", 1)[0].replace("-", "_")
    return render


def make_link_banner_renderer(image_filename: str, url: str):
    """Return a section renderer that emits a centered, clickable banner on its own page."""
    def render(data: "KundliData", lang: str = "en") -> str | None:
        template = make_env().get_template("offer_banner.html")
        return template.render(image=image_filename, url=url, lang=lang)

    render.__name__ = "render_banner_" + image_filename.rsplit(".", 1)[0].replace("-", "_")
    return render

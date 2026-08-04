from __future__ import annotations

import pytest

from demo_data import SAMPLE_KUNDLI_DATA
from pdf_generator import PDFGenerator


@pytest.fixture
def generator() -> PDFGenerator:
    return PDFGenerator()


def test_pdf_generated_and_valid(generator: PDFGenerator) -> None:
    pdf = generator.generate(SAMPLE_KUNDLI_DATA, "en")
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 50_000


def test_pdf_hindi_output(generator: PDFGenerator) -> None:
    pdf = generator.generate(SAMPLE_KUNDLI_DATA, "hi")
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 50_000


def test_pdf_with_subset_sections(generator: PDFGenerator) -> None:
    pdf = generator.generate(
        SAMPLE_KUNDLI_DATA, "en",
        include_sections=["cover", "planets"],
    )
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 10_000


def test_pdf_with_empty_data(generator: PDFGenerator) -> None:
    from models import KundliData, KundliRequest

    empty_data = KundliData(
        request=KundliRequest(
            name="Empty", day=1, month=1, year=2000,
            hour=0, min=0, lat=0.0, lon=0.0, tzone=0.0,
        )
    )
    pdf = generator.generate(empty_data, "en")
    assert pdf[:5] == b"%PDF-"


TESTABLE_SECTIONS = [
    "three_pillars",
    "sade_sati_journey",
    "mahadasha_journey",
    "numerology_personality",
    "remedy_rudraksha",
    "remedy_gemstones",
    "remedy_mantras",
    "remedy_yantra",
    "remedy_daan",
    "career_path",
    "marriage_timing",
    "material_comforts",
]


@pytest.mark.parametrize("section_name", TESTABLE_SECTIONS)
def test_section_renders_without_error(generator: PDFGenerator, section_name: str) -> None:
    pdf = generator.generate(SAMPLE_KUNDLI_DATA, "en", [section_name])
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000


@pytest.mark.parametrize("section_name", TESTABLE_SECTIONS)
def test_section_renders_hindi(generator: PDFGenerator, section_name: str) -> None:
    pdf = generator.generate(SAMPLE_KUNDLI_DATA, "hi", [section_name])
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000


# Both renderers read the module-level `config.settings` singleton, which is populated from
# the developer's real .env. Without patching, these tests assert "no AUTHOR_NAME configured"
# on a machine where AUTHOR_NAME *is* configured, so they pass only against an empty .env.
# Patching the attribute makes each test assert its own branch either way.


def test_authors_note_skips_without_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from config import settings
    from sections.authors_note import render_authors_note

    monkeypatch.setattr(settings, "author_name", "")
    assert render_authors_note(SAMPLE_KUNDLI_DATA, "en") is None


def test_authors_note_renders_with_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """AUTHOR_NAME is a gate, not content: templates/authors_note.html is an image-based
    page and does not print the name. So this asserts the section appears, nothing more."""
    from config import settings
    from sections.authors_note import render_authors_note

    monkeypatch.setattr(settings, "author_name", "Pandit Test")
    monkeypatch.setattr(settings, "author_title", "Jyotish Acharya")

    result = render_authors_note(SAMPLE_KUNDLI_DATA, "en")
    assert result is not None
    assert "authors-note-page" in result


def test_closing_cta_skips_without_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from config import settings
    from sections.closing_cta import render_closing_cta

    monkeypatch.setattr(settings, "cta_consult_url", "")
    monkeypatch.setattr(settings, "cta_pooja_url", "")
    monkeypatch.setattr(settings, "cta_rudraksha_url", "")
    assert render_closing_cta(SAMPLE_KUNDLI_DATA, "en") is None


@pytest.mark.parametrize("field", ["cta_consult_url", "cta_pooja_url", "cta_rudraksha_url"])
def test_closing_cta_renders_with_any_single_url(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Any one URL alone is enough — the renderer's guard is an `and` over the absences."""
    from config import settings
    from sections.closing_cta import render_closing_cta

    for f in ("cta_consult_url", "cta_pooja_url", "cta_rudraksha_url"):
        monkeypatch.setattr(settings, f, "")
    monkeypatch.setattr(settings, field, "https://example.test/x")
    assert render_closing_cta(SAMPLE_KUNDLI_DATA, "en") is not None


# --- Table of contents -------------------------------------------------------
#
# The TOC is derived from the sections that actually rendered (see DEFERRED_SECTIONS
# in pdf_generator). The guards below are the point of that design: they turn the
# next section addition into a failing test instead of a TOC that silently advertises
# a page the PDF doesn't contain.

from pdf_generator import IMAGE_ONLY_SECTIONS, SECTION_RENDERERS  # noqa: E402
from sections import LOCALES, TOC_CHAPTERS  # noqa: E402
from sections.front_matter import build_toc_items, render_front_matter_toc  # noqa: E402

# Sections deliberately absent from the TOC: front matter, back matter, and the
# full-page divider/banner artwork. Adding a *content* renderer without claiming it in
# TOC_CHAPTERS must fail test_every_content_section_is_in_a_toc_chapter — do not park
# it here to silence that.
UNLISTED_SECTIONS = {
    "front_page", "astrologer_intro", "authors_note", "front_matter", "cover",
    "front_matter_toc", "divider_ganesha", "divider_grah", "divider_dosha",
    "offer_banner", "divider_numerology", "divider_lalkitab", "closing_cta",
}

_ALL_SECTIONS = [name for name, _ in SECTION_RENDERERS]
_CONTENT_SECTIONS = [n for n in _ALL_SECTIONS if n not in UNLISTED_SECTIONS]
_CHAPTER_MEMBERS = [m for _, members in TOC_CHAPTERS for m in members]


def test_toc_members_exist_in_section_renderers() -> None:
    assert set(_CHAPTER_MEMBERS) <= set(_ALL_SECTIONS), \
        set(_CHAPTER_MEMBERS) - set(_ALL_SECTIONS)


def test_every_content_section_is_in_a_toc_chapter() -> None:
    assert set(_CONTENT_SECTIONS) == set(_CHAPTER_MEMBERS), {
        "unclaimed": sorted(set(_CONTENT_SECTIONS) - set(_CHAPTER_MEMBERS)),
        "not_a_content_section": sorted(set(_CHAPTER_MEMBERS) - set(_CONTENT_SECTIONS)),
    }


def test_no_section_claimed_by_two_chapters() -> None:
    assert len(_CHAPTER_MEMBERS) == len(set(_CHAPTER_MEMBERS))


def test_toc_chapter_order_follows_section_renderers() -> None:
    """A chapter's row position must match its first member's page position."""
    firsts = [min(_CONTENT_SECTIONS.index(m) for m in members) for _, members in TOC_CHAPTERS]
    assert firsts == sorted(firsts), [key for key, _ in TOC_CHAPTERS]


def test_toc_chapter_members_are_contiguous() -> None:
    """Non-contiguous members would make TOC row order disagree with print order."""
    for key, members in TOC_CHAPTERS:
        idx = sorted(_CONTENT_SECTIONS.index(m) for m in members)
        assert idx == list(range(idx[0], idx[0] + len(idx))), key


def test_toc_chapters_never_depend_on_image_only_sections() -> None:
    """Keeps PDF_IMAGES_ENABLED=false from changing the TOC."""
    assert not (set(_CHAPTER_MEMBERS) & IMAGE_ONLY_SECTIONS)


@pytest.mark.parametrize("lang", ["en", "hi"])
def test_every_toc_chapter_has_strings(lang: str) -> None:
    strings = LOCALES[lang]["fm_toc_items"]
    for key, _ in TOC_CHAPTERS:
        assert key in strings, (lang, key)
        assert strings[key]["name"] and strings[key]["desc"], (lang, key)


@pytest.mark.parametrize("lang", ["en", "hi"])
def test_no_orphan_toc_strings(lang: str) -> None:
    assert set(LOCALES[lang]["fm_toc_items"]) == {key for key, _ in TOC_CHAPTERS}


def test_toc_keys_match_across_languages() -> None:
    assert set(LOCALES["en"]["fm_toc_items"]) == set(LOCALES["hi"]["fm_toc_items"])


def test_toc_lists_all_chapters_when_rendered_set_unknown() -> None:
    """The 2-arg renderer(data, lang) contract the render loop relies on."""
    assert len(build_toc_items("en", None)) == len(TOC_CHAPTERS)
    html = render_front_matter_toc(SAMPLE_KUNDLI_DATA, "en")
    assert html.count('class="toc-num"') == len(TOC_CHAPTERS)


def test_toc_omits_chapters_whose_sections_did_not_render() -> None:
    items = build_toc_items("en", {"astro_details", "numerology"})
    assert [i["name"] for i in items] == ["Birth Summary", "Numerology"]


def test_toc_keeps_chapter_when_only_one_member_rendered() -> None:
    """"Remedies" covers five renderers; any one of them earns the row."""
    assert [i["name"] for i in build_toc_items("en", {"remedy_daan"})] == ["Remedies"]


def test_toc_numbering_is_contiguous_after_omissions() -> None:
    html = render_front_matter_toc(
        SAMPLE_KUNDLI_DATA, "en", rendered_sections={"astro_details", "yogas"}
    )
    assert html.count('class="toc-num"') == 2
    assert 'class="toc-num">1</span>' in html
    assert 'class="toc-num">2</span>' in html


def test_toc_is_empty_for_empty_rendered_set() -> None:
    assert build_toc_items("en", set()) == []
    assert "toc-row" not in render_front_matter_toc(
        SAMPLE_KUNDLI_DATA, "en", rendered_sections=set()
    )


def test_toc_falls_back_to_english_for_missing_translation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hi_items = dict(LOCALES["hi"]["fm_toc_items"])
    hi_items.pop("yogas")
    monkeypatch.setitem(LOCALES["hi"], "fm_toc_items", hi_items)
    assert any(i["name"] == "Yoga Analysis" for i in build_toc_items("hi", None))

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Smart Kundli is a FastAPI service that generates Vedic birth chart (Kundli) and match-making (Kundli Milan) PDF reports. It fetches data from AstrologyAPI (astrologyapi.com), renders HTML sections via Jinja2, and converts to PDF with WeasyPrint.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server (Windows — needs MSYS2 Pango in PATH)
start.bat
# or manually:
set PATH=C:\msys64\mingw64\bin;%PATH%
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
pytest tests/ -v

# Run a single test
pytest tests/test_main.py::test_health -v

# Quick smoke test (no API key needed)
curl http://localhost:8000/demo -o demo.pdf
```

## Architecture

### Two PDF pipelines

1. **Kundli (birth chart):** `POST /generate-kundli` -> `AstrologyAPIClient.fetch_all()` -> `KundliData` -> `PDFGenerator` (62 section renderers in `SECTION_RENDERERS`)
2. **Match-making:** `POST /generate-match` -> `AstrologyAPIClient.fetch_match()` -> `MatchData` -> `MatchPDFGenerator` (single `render_matching` section)

Both share `base.html` + `styles.css` for final HTML->PDF conversion via WeasyPrint.

### API data fetching (`api_client.py`)

`fetch_all()` runs in 3 phases to respect data dependencies:
- **Phase 1:** 81 independent parallel API calls via `asyncio.gather()` (birth details, planets, panchang, dasha, doshas, remedies, numerology, Lal Kitab, biorhythm, etc.)
- **Phase 2:** Per-planet and per-chart parallel calls (7 planet ashtakvarga + 17 divisional charts + chart images + 9 house/rashi reports + 9 Lal Kitab remedies)
- **Phase 3:** Sub-dasha calls that depend on Phase 1 results (Vimshottari sub-periods need current dasha planet names; Char Dasha sub-periods need current sign)

Concurrency is bounded by an `asyncio.Semaphore(10)` — at most 10 API calls in flight. All calls use `tenacity` retry with exponential backoff, only retrying on 5xx/429 and connection/timeout errors.

### Key design decisions

- **Graceful degradation:** Every API call is individually try/excepted; if one fails, that section is skipped but the PDF still generates with remaining sections.
- `_houses_from_planets()` derives house data from planet positions when the `/houses` endpoint fails — a fallback, not a redundancy.
- `_normalize_planet_names()` overrides API-returned planet names with English canonical names from `PLANET_ID_TO_EN` (the API returns Hindi names when `lang=hi`).
- PDF generation runs in `asyncio.to_thread()` because WeasyPrint is blocking.
- Two payload variants: `payload` (basic birth params) and `payload_with_ayan` (adds `ayanamsha: "LAHIRI"`). Numerology uses a separate `numero_payload` (day/month/year/name, no coordinates).

### Section rendering pattern

Each file in `sections/` exports a `render_<name>(data: KundliData, lang: str) -> str | None` function. It loads its own Jinja2 template from `templates/`, passes locale strings from `sections/__init__.py` LOCALES dict, and returns rendered HTML or `None` to skip.

**To add a new section:**
1. Create `templates/new_section.html`
2. Create `sections/new_section.py` with `render_new_section(data, lang)` function
3. Add the renderer to `SECTION_RENDERERS` list in `pdf_generator.py`
4. Add locale strings for both `"en"` and `"hi"` keys in `LOCALES` dict in `sections/__init__.py`

### Narrative engine (`narrative_engine.py`)

AI-generated personalized narratives for 20+ section types using Claude Sonnet via the Anthropic SDK (`AsyncAnthropic`). Requires `ANTHROPIC_API_KEY` in `.env` — skips gracefully if not set.

- **Concurrency:** `asyncio.Semaphore(5)` limits parallel API calls, each with 30s timeout.
- **Caching:** Async SQLite cache (`narrative_cache.db`) keyed by SHA-256 of section type + data + lang. Avoids re-generating identical narratives across runs.
- **Bilingual:** Separate system prompts for English and Hindi. Hindi prompt enforces pure Devanagari with no English words.
- **Tone:** Warm, conversational, non-preachy. Saturn challenges = "growth invitations", Manglik = "your inner fire", Sade Sati = "a 7.5-year masterclass". Forbidden: death predictions, exact bad-event dates, fear-inducing content.
- **Section types:** planet placement, mahadasha period, raj yoga, three pillars (lagna/moon/nakshatra), sade sati phases, raj yoga celebration, mahadasha journey (structured JSON with experience/avoid bullets), numerology personality, rudraksha/gemstone/mantra/ishta devata/yantra/daan guidance, outer planet, marriage timing, career path, love marriage, spiritual potential, rahu-ketu analysis, life forecast.
- **Translation pipeline:** `translate_reports()` batch-translates English API report text (ascendant, nakshatra, house, rashi reports) to Hindi for `lang=hi` PDFs.

### Remedies journey

Six dedicated remedy sections: `remedy_rudraksha`, `remedy_gemstones`, `remedy_mantras`, `remedy_ishta_devata`, `remedy_yantra`, `remedy_daan`. Each has its own narrative and shares `templates/partials/remedy_disclaimer.html`. The daan section cross-references dosha API data (Manglik, Sadhesati, Pitra, Kalsarpa, planet_nature BAD/KILLER, Angarak, Shrapit, Guru-Chandal, Grahan doshas) alongside dignity-based weak planet detection. Shared constants live in `sections/remedy_constants.py`.

### Outer planets

`sections/outer_planets.py` renders Uranus, Neptune, and Pluto with Vedic deity framing (Arun Dev, Varun Dev, Yama/Shiva). Uses `data.planets_extended or data.planets` — the real API returns outer planets via the `/planets/extended` endpoint into `planets_extended`, while demo data includes them in `planets`.

### Commercial polish (Phase 6)

Three conditional sections controlled by `.env` settings:
- **Author's Note** (`sections/authors_note.py`) — warm welcome letter. Requires `AUTHOR_NAME`.
- **Closing CTA** (`sections/closing_cta.py`) — consultation + pooja booking cards. Requires `CTA_CONSULT_URL` or `CTA_POOJA_URL`.
- **Branded footer** — company name, URL, phone on every page (except cover) via CSS `@page` margin boxes in `base.html`. Requires `BRAND_FOOTER_ENABLED=true`.

All return `None` / skip when settings are empty — no visual artifacts in the PDF.

### Section disclaimers

Two disclaimer partials in `templates/partials/`:
- `remedy_disclaimer.html` — remedy-specific, included in 6 remedy templates.
- `section_disclaimer.html` — warm general analysis disclaimer, included in 8 major section templates (dosha, yogas, dasha, life_forecast, marriage_timing, career_path, love_marriage, spiritual_potential).

### Bilingual support

English and Hindi. `sections/__init__.py` exports `LOCALES` dict, sign/planet name mappings (`SIGN_NAMES_BY_ID`, `SIGN_NAMES_HI_BY_ID`, `PLANET_SHORT_EN`, `PLANET_SHORT_HI`), and helper `build_sign_planet_map()` for chart rendering. Hindi section renderers pass both `planet_names` (Hindi) and `planet_names_en` (English originals) to templates for dual-script display.

### Frontend

`static/index.html` serves at `/` — a form UI for generating kundli and match PDFs. Uses `/api/geo-search` for place autocomplete and `/api/timezone` for DST-aware timezone lookup.

## Configuration

Settings via pydantic-settings in `config.py`, loaded from `.env`. Required: `ASTRO_API_KEY`. See `.env.example` for all options.

Key optional settings:
- `ANTHROPIC_API_KEY` — enables AI narrative generation and Hindi report translation.
- `AUTHOR_NAME`, `AUTHOR_TITLE` — enables Author's Note page.
- `CTA_CONSULT_URL`, `CTA_POOJA_URL` — enables Closing CTA page.
- `BRAND_FOOTER_ENABLED`, `BRAND_FOOTER_NAME`, `BRAND_FOOTER_URL`, `BRAND_FOOTER_PHONE` — enables branded footer on every page.

**Important:** Settings must be in `.env` (not `.env.example`) to take effect. `.env.example` is documentation only.

## Windows Dependency

WeasyPrint requires MSYS2 Pango (`C:\msys64\mingw64\bin` must be in PATH). The `start.bat` script handles this.

## Testing

Tests use `pytest` + `pytest-asyncio`. API client tests use `respx` to mock httpx. The `/demo` endpoint uses hardcoded sample data from `demo_data.py` and requires no API key — `test_demo_pdf` validates end-to-end PDF generation.

`tests/test_pdf_generator.py` has 44 tests:
- Full PDF generation (en + hi) and subset section tests.
- Parametrized per-section rendering: 19 sections × 2 languages (en + hi) — each section rendered individually with demo data.
- Conditional skip tests: `authors_note` returns `None` without `AUTHOR_NAME`, `closing_cta` returns `None` without CTA URLs.

**Note on Windows:** When running pytest, ensure MSYS2 Pango is in PATH but the system Python comes first (append `C:\msys64\mingw64\bin` to end of PATH, not beginning).

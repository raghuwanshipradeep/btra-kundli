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

# Run prod-style server (4 workers, no reload)
start_prod.bat

# Run all tests
pytest tests/ -v

# Run a single test
pytest tests/test_main.py::test_health -v

# Quick smoke test (no API key needed)
curl http://localhost:8000/demo -o demo.pdf

# QA-check a generated PDF (uses pdftotext; flags rendering/content issues)
python qa_check.py demo.pdf
```

## Architecture

### Two PDF pipelines

1. **Kundli (birth chart):** `POST /generate-kundli` -> `AstrologyAPIClient.fetch_all()` -> `KundliData` -> `PDFGenerator` (57 entries in `SECTION_RENDERERS`: 49 content renderers + 8 divider/banner image renderers)
2. **Match-making:** `POST /generate-match` -> `AstrologyAPIClient.fetch_match()` -> `MatchData` -> `MatchPDFGenerator` (single `render_matching` section)

Both share `base.html` + `styles.css` for final HTML->PDF conversion via WeasyPrint.

`POST /generate-kundli` is gated behind `allow_free_generation` (403 unless enabled) — in production the real entry point is the paid flow below. The reusable pipeline lives in `_build_kundli_pdf()` in `main.py`: fetch -> `generate_narratives()` -> `translate_reports()` -> `pdf_gen.generate()`.

### Report tiers

`KundliRequest.report_tier` is `"detailed"` (default) or `"lite"`. `PDFGenerator.generate(..., report_tier=...)` skips the section names in `LITE_SKIP_SECTIONS` (`pdf_generator.py`) when tier is `"lite"`.

### API data fetching (`api_client.py`)

`fetch_all()` runs in 3 phases to respect data dependencies:
- **Phase 1:** ~61 independent parallel API calls via one `asyncio.gather()` (75 slots, 14 of which are `_skip()` placeholders for retired sections) (birth details, planets, panchang, dasha, doshas, remedies, numerology, Lal Kitab, biorhythm, etc.)
- **Phase 2:** Per-planet and per-chart parallel calls (7 planet ashtakvarga + 17 divisional charts + chart images + 9 house/rashi reports + 9 Lal Kitab remedies)
- **Phase 3:** Sub-dasha calls that depend on Phase 1 results (Vimshottari sub-periods need current dasha planet names; Char Dasha sub-periods need current sign)

Concurrency is bounded by an `asyncio.Semaphore(10)` — at most 10 API calls in flight. All calls use `tenacity` retry with exponential backoff, only retrying on 5xx/429 and connection/timeout errors.

### Key design decisions

- **Graceful degradation:** Every API call is individually try/excepted; if one fails, that section is skipped but the PDF still generates with remaining sections.
- `_houses_from_planets()` derives house data from planet positions when the `/houses` endpoint fails — a fallback, not a redundancy.
- `_normalize_planet_names()` overrides API-returned planet names with English canonical names from `PLANET_ID_TO_EN` (the API returns Hindi names when `lang=hi`).
- PDF generation runs in `asyncio.to_thread()` because WeasyPrint is blocking, and simultaneous renders are capped by `generation_concurrency` (`_get_generation_slots()` in `pipeline.py`).
- **Filler images:** `_fill_gap_pages()` in `pdf_generator.py` overlays promo images on pages that come out mostly blank. Controlled by `filler_images_enabled`, `filler_gap_threshold`, `filler_skip_pages`.
- Two payload variants: `payload` (basic birth params) and `payload_with_ayan` (adds `ayanamsha: "LAHIRI"`). Numerology uses a separate `numero_payload` (day/month/year/name, no coordinates).

### Section rendering pattern

Each file in `sections/` exports a `render_<name>(data: KundliData, lang: str) -> str | None` function. It loads its own Jinja2 template from `templates/`, passes locale strings from `sections/__init__.py` LOCALES dict, and returns rendered HTML or `None` to skip.

**To add a new section:**
1. Create `templates/new_section.html`
2. Create `sections/new_section.py` with `render_new_section(data, lang)` function
3. Add the renderer to `SECTION_RENDERERS` list in `pdf_generator.py`
4. Add locale strings for both `"en"` and `"hi"` keys in `LOCALES` dict in `sections/__init__.py`

### Payment, fulfillment, and delivery (`main.py`)

Production flow is paid, asynchronous, and fire-and-forget for the customer:

1. `POST /create-order` — creates a Razorpay order, stores the `KundliRequest` in the in-memory `_ORDER_STORE` (30-min TTL) keyed by `order_id`. Returns checkout params to the browser. (`GET /api/payment-config` exposes the Razorpay key id + price to the frontend.)
2. Payment confirmation arrives via **two** independent paths: the in-page `POST /verify-and-generate` callback (best-effort fast path, verifies the checkout HMAC signature) and `POST /razorpay-webhook` (reliable server-to-server, verifies the webhook HMAC over the raw body — a *different* secret). Both call `_start_fulfillment()`.
3. `_start_fulfillment()` is idempotent via `_claim_order()` (a `set` check-and-add with no `await` between, so atomic in one worker) — whichever path arrives first wins, the other is a no-op. It schedules two `BackgroundTasks`: `notify_payment_success` (Pabbly, registered first so downstream automation fires immediately) then `_generate_and_archive`.
4. `_generate_and_archive()` runs `_build_kundli_pdf()` under a `generation_timeout_seconds` wall, uploads to Google Drive, and records progress in the in-memory `_JOB_STATE` dict (`generating` -> `archived` / `timeout` / `pdf_failed` / `drive_failed` / `generated_no_archive`). On Drive failure it writes the paid PDF to `drive_recovery_dir` so it's never lost.

`/admin/jobs` and `/admin/jobs/{order_id}` expose `_JOB_STATE` for ops, gated by the `X-Admin-Key` header matching `admin_key`.

**Caveat:** `_ORDER_STORE`, `_FULFILLED_ORDERS`, and `_JOB_STATE` are process-local dicts — they do not survive a restart and break under multiple workers. The code comments flag Redis/SQLite as the production fix.

Archive filenames are `First##Phone##Email##OrderId.pdf` (`_build_filename()` in `pipeline.py`; order id is appended in the paid flow and omitted in the free/dev flow).

The reusable pipeline (`_build_kundli_pdf`, `_build_filename`, `_save_recovery_pdf`, `_get_generation_slots`) lives in `pipeline.py` so both `main.py` and the standalone sheet sweeper import it **without** importing the FastAPI `app`.

### Sheet-driven kundli generation (standalone sweeper)

A second producer alongside the paid Razorpay flow. A Google Apps Script (`scripts/sheet_to_supabase.gs`) syncs orders into Supabase `sheet_orders` (schema: `sheet_orders_schema.sql`). The worker `sheet_worker.sweep_once()` reads SUCCESSFUL rows, maps each via the pure `sheet_mapper.map_sheet_row()`, runs the shared `pipeline._build_kundli_pdf()`, and archives to Drive with amount-based routing (`folder_for_amount()` in `drive_uploader.py`). Status lives in the `sheet_orders.kundli_*` columns; `kundli_orders` and the paid flow are untouched.

- **How it runs:** `run_sweeper.py` is a dedicated 24/7 async loop (`start_sweeper.bat`) that calls `sweep_once()` every `SHEET_SWEEP_INTERVAL_SECONDS`. Run **exactly one** instance — never replicas — because the in-process `_SHEET_WORKER_LOCK` + the `kundli_*` columns are what prevent double-generation. The web app stays `--workers 4`; the sweeper is a separate process.
- **Manual trigger:** `POST /admin/process-sheet-orders` (X-Admin-Key) calls the same `sweep_once()` for on-demand drains or single-order tests (`?limit=1`).
- **Idempotency/recovery:** a claimed row stuck in `generating` is reclaimed by `reclaim_stale()` after `generation_timeout_seconds`; bad birth data is parked `failed_permanent` (no retry) *before* any API spend; transient failures retry up to `SHEET_ORDERS_KUNDLI_MAX_ATTEMPTS`.
- **Kill switch:** `SHEET_SWEEPER_ENABLED=false` idles the loop without a restart. **Observability:** `GET /admin/sheet-jobs` (X-Admin-Key) lists failed/parked rows with `sheet_row` to trace back to the sheet cell.
- **Relationship to `INLINE_GENERATION_ENABLED`:** set it `false` so the paid form flow only records + notifies and lets this sweeper generate, avoiding double-generation.

- **Drive archive** (`drive_uploader.py`): `upload_kundli_pdf()` uploads to `google_drive_folder_id` via OAuth (`token.json` / `oauth_credentials.json`). Returns `None` on any failure (never raises into fulfillment). `get_drive_token.py` mints the token; see the Coolify/Drive memory and `DEPLOYMENT.md` for the prod re-auth flow.
- **Pabbly** (`pabbly_notifier.py`): `notify_payment_success()` POSTs a payment-success payload to `pabbly_webhook_url` for downstream automation (WhatsApp/CRM/sheets). Disabled when the URL is empty.
- **Supabase audit** (`supabase_repo.py`): records each paid order's lifecycle (created -> paid -> generating -> archived/failed) in the `kundli_orders` table via the PostgREST API with the service key — a durable complement to the in-memory stores. Best-effort like Drive/Pabbly: never raises into fulfillment; disabled unless both `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are set.

### Narrative engine (`narrative_engine.py`)

AI-generated personalized narratives for 20+ section types via the Anthropic SDK (`AsyncAnthropic`). Requires `ANTHROPIC_API_KEY` in `.env` — skips gracefully if not set. All three model constants (`NARRATIVE_MODEL`, `TRANSLATION_MODEL`, `SIMPLE_NARRATIVE_MODEL`) are now hardcoded to Haiku 4.5 (`claude-haiku-4-5-20251001`) for cost — Sonnet is no longer used, so the `use_haiku_for_translation` / `use_haiku_for_simple_narratives` settings are vestigial (both branches resolve to Haiku). See `docs/cost-optimization-results.md`.

- **Concurrency:** `asyncio.Semaphore(5)` limits parallel API calls, each with 30s timeout.
- **Caching:** Async SQLite cache (`narrative_cache.db`) keyed by SHA-256 of section type + data + lang. Avoids re-generating identical narratives across runs.
- **Bilingual:** Separate system prompts for English and Hindi. Hindi prompt enforces pure Devanagari with no English words.
- **Tone:** Warm, conversational, non-preachy. Saturn challenges = "growth invitations", Manglik = "your inner fire", Sade Sati = "a 7.5-year masterclass". Forbidden: death predictions, exact bad-event dates, fear-inducing content.
- **Section types:** planet placement, mahadasha period, raj yoga, three pillars (lagna/moon/nakshatra), sade sati phases, raj yoga celebration, mahadasha journey (structured JSON with experience/avoid bullets), numerology personality, rudraksha/gemstone/mantra/ishta devata/yantra/daan guidance, outer planet, marriage timing, career path, love marriage, spiritual potential, rahu-ketu analysis.
- **Translation pipeline:** `translate_reports()` batch-translates English API report text (ascendant, nakshatra, house, rashi reports) to Hindi for `lang=hi` PDFs.

### Remedies journey

Five dedicated remedy sections: `remedy_rudraksha`, `remedy_gemstones`, `remedy_mantras`, `remedy_yantra`, `remedy_daan`. (The Ishta Devata deity/shloka is shown inside `remedy_mantras`, not as its own section.) Each has its own narrative and shares `templates/partials/remedy_disclaimer.html`. The daan section cross-references dosha API data (Manglik, Sadhesati, Pitra, Kalsarpa, planet_nature BAD/KILLER, Angarak, Shrapit, Guru-Chandal, Grahan doshas) alongside dignity-based weak planet detection. Shared constants live in `sections/remedy_constants.py`.

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
- `section_disclaimer.html` — warm general analysis disclaimer, included in 6 major section templates (dosha, yogas, dasha, marriage_timing, career_path, spiritual_potential).

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
- `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `KUNDLI_PRICE_PAISE` — enables the paid generation flow. `ALLOW_FREE_GENERATION=true` re-opens the unauthenticated `/generate-kundli` endpoint (off in prod).
- `GOOGLE_DRIVE_FOLDER_ID`, `GOOGLE_DRIVE_FOLDER_ID_PREMIUM`, `DRIVE_PREMIUM_AMOUNT_THRESHOLD`, `DRIVE_ARCHIVE_ENABLED`, `DRIVE_RECOVERY_DIR` — Drive archive of paid PDFs (premium routing by order amount).
- `PABBLY_WEBHOOK_URL` — downstream payment-success automation.
- `ADMIN_KEY` — required to access `/admin/jobs*` and `/admin/sheet-jobs`.
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` — enable the Supabase audit layer and the sheet-driven worker (both required).
- `SHEET_SWEEPER_ENABLED` (kill switch), `SHEET_SWEEP_INTERVAL_SECONDS`, `SHEET_ORDERS_TABLE`, `SHEET_ORDERS_KUNDLI_MAX_ATTEMPTS` — the standalone `run_sweeper.py` process.

**Important:** Settings must be in `.env` (not `.env.example`) to take effect. `.env.example` is documentation only. See `DEPLOYMENT.md` for the Coolify production setup (Drive OAuth via file mounts, re-auth flow).

## Windows Dependency

WeasyPrint requires MSYS2 Pango (`C:\msys64\mingw64\bin` must be in PATH). The `start.bat` script handles this.

## Testing

Tests use `pytest` + `pytest-asyncio`. API client tests use `respx` to mock httpx. The `/demo` endpoint uses hardcoded sample data from `demo_data.py` and requires no API key — `test_demo_pdf` validates end-to-end PDF generation.

`tests/test_pdf_generator.py` has 36 tests:
- Full PDF generation (en + hi) and subset section tests.
- Parametrized per-section rendering: 15 sections × 2 languages (en + hi) — each section rendered individually with demo data.
- Conditional skip tests: `authors_note` returns `None` without `AUTHOR_NAME`, `closing_cta` returns `None` without CTA URLs.

Other suites in `tests/`: `test_dignity`, `test_pdf_qa`, `test_drive_uploader`, `test_supabase_repo`, `test_webhook` (payment paths), `test_sheet_mapper`, `test_sheet_worker`, `test_sheet_orders_repo`. `test_pabbly.py` sits at the repo root, outside the pytest default path.

**Note on Windows:** When running pytest, ensure MSYS2 Pango is in PATH but the system Python comes first (append `C:\msys64\mingw64\bin` to end of PATH, not beginning).

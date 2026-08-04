# Smart Kundli — Vedic Birth Chart & Match-Making PDF Report Generator

A production-quality Python application that generates beautifully formatted Kundli (Vedic birth chart) and Kundli Milan (match-making) PDF reports using the AstrologyAPI.

## Features

- **81+ parallel API calls** via `asyncio.gather()` with semaphore-bounded concurrency (max 10 in-flight)
- **51-section PDF report** with professional Indian astrology styling
- **Match-making (Kundli Milan)** compatibility report for two people
- **Frontend UI** with place autocomplete and DST-aware timezone lookup
- **Bilingual support**: English and Hindi (Devanagari)
- **Graceful degradation**: failed API calls skip that section, PDF still generates
- **WeasyPrint rendering**: HTML/CSS to print-quality A4 PDF
- **Retry with exponential backoff** (tenacity) on 5xx/429 and connection errors

## Report Sections

The Kundli PDF contains up to 51 sections, grouped by category:

| Category | Sections |
|----------|----------|
| Core | Cover, Front Matter, Birth Summary, Panchang |
| Charts | Lagna (D1), Divisional Charts, Moon Chart, South Indian, North Indian |
| Planets & Houses | Planetary Positions, House Positions, Astro Details, Bhav Madhya, Planet Nature, Dignity, Chara Karaka |
| Relationships | Panchada Maitri, Tatkalik Maitri, Drishti (Aspects) |
| Dasha Systems | Vimshottari Dasha, Yogini Dasha, Char Dasha, Dasha Narrative |
| Ashtakvarga | Sarva Ashtakavarga, Bhinnashtak |
| Doshas & Remedies | Dosha, Extended Dosha, Remedies, Extended Remedies, Lal Kitab |
| Life Reports | Life Reports, Graha Profile, Daily Predictions, Varshaphal |
| Special | KP Birth Chart, Numerology, Biorhythm, Ghat Chakra, Avakhada Chakra |
| Advanced | Yogas, Graha Sanyog, Rahu-Ketu Analysis, Sadhesati Enhanced |
| Life Events | Career Path, Marriage Timing, Love Marriage, Life Forecast, Spiritual Potential |
| Extra | Shodashvarga Summary, Thematic Reports, Tarot |

## Prerequisites

- Python 3.11+
- MSYS2 with Pango (for WeasyPrint on Windows)
- AstrologyAPI account ([astrologyapi.com](https://astrologyapi.com))

### Windows: Install WeasyPrint dependencies

```bash
# Install MSYS2 (if not installed)
winget install MSYS2.MSYS2

# Install Pango via MSYS2
C:\msys64\usr\bin\bash.exe -lc "pacman -S --noconfirm mingw-w64-x86_64-pango"

# Add to PATH (run in PowerShell as admin, or add to system environment variables)
$env:PATH = "C:\msys64\mingw64\bin;$env:PATH"
```

## Installation

```bash
cd smart_kundli
pip install -r requirements.txt
```

**Dependencies:**
- fastapi, uvicorn — Web framework & ASGI server
- httpx — Async HTTP client for AstrologyAPI
- weasyprint — HTML/CSS to PDF rendering
- jinja2 — HTML templating
- pydantic, pydantic-settings — Data validation & configuration
- python-dotenv — Environment variable loading
- tenacity — Retry logic with exponential backoff
- pytest, pytest-asyncio, respx — Testing

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `ASTRO_API_BASE_URL` | `https://json.astrologyapi.com/v1` | AstrologyAPI base URL |
| `ASTRO_API_KEY` | *(required)* | Your AstrologyAPI key |
| `ASTRO_API_TIMEOUT` | `30` | Request timeout in seconds |
| `ASTRO_API_MAX_RETRIES` | `3` | Max retry attempts on failure |
| `DEFAULT_LANG` | `hi` | Default language (`en` or `hi`) |
| `LOG_LEVEL` | `INFO` | Logging level |

## Running

```bash
# Using start.bat (Windows — handles PATH automatically)
start.bat

# Or manually:
set PATH=C:\msys64\mingw64\bin;%PATH%
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 for the frontend UI.

## API Endpoints

### `GET /`
Frontend UI — form for generating Kundli and Match PDFs with place autocomplete.

### `GET /health`
Health check. Returns `{"status": "ok", "version": "1.0.0"}`.

### `GET /demo`
Generate a demo PDF with sample data (no API key needed).

### `GET /api/geo-search?place=<query>`
Location search with autocomplete. Returns matching places with coordinates.

### `GET /api/timezone`
DST-aware timezone lookup for given datetime and coordinates.

**Query params:** `day`, `month`, `year`, `hour`, `min`, `lat`, `lon`, `tzone`

### `POST /generate-kundli`
Generate a Kundli (birth chart) PDF report.

**Request body:**
```json
{
  "name": "Rahul Sharma",
  "day": 15,
  "month": 8,
  "year": 1990,
  "hour": 14,
  "min": 30,
  "lat": 23.1765,
  "lon": 75.7885,
  "tzone": 5.5,
  "lang": "en",
  "place": "Ujjain"
}
```

**Response:** PDF file (`application/pdf`)

**Example with curl:**
```bash
curl -X POST http://localhost:8000/generate-kundli \
  -H "Content-Type: application/json" \
  -d '{"name":"Rahul Sharma","day":15,"month":8,"year":1990,"hour":14,"min":30,"lat":23.1765,"lon":75.7885,"tzone":5.5,"lang":"en","place":"Ujjain"}' \
  -o kundli.pdf
```

### `POST /generate-match`
Generate a Kundli Milan (match-making) compatibility PDF for two people.

**Request body:**
```json
{
  "m_name": "Rahul Sharma",
  "m_day": 15,
  "m_month": 8,
  "m_year": 1990,
  "m_hour": 14,
  "m_min": 30,
  "m_lat": 23.1765,
  "m_lon": 75.7885,
  "m_tzone": 5.5,
  "f_name": "Priya Verma",
  "f_day": 22,
  "f_month": 3,
  "f_year": 1992,
  "f_hour": 9,
  "f_min": 15,
  "f_lat": 28.6139,
  "f_lon": 77.2090,
  "f_tzone": 5.5,
  "lang": "en"
}
```

**Response:** PDF file (`application/pdf`)

**Example with curl:**
```bash
curl -X POST http://localhost:8000/generate-match \
  -H "Content-Type: application/json" \
  -d '{"m_name":"Rahul","m_day":15,"m_month":8,"m_year":1990,"m_hour":14,"m_min":30,"m_lat":23.1765,"m_lon":75.7885,"m_tzone":5.5,"f_name":"Priya","f_day":22,"f_month":3,"f_year":1992,"f_hour":9,"f_min":15,"f_lat":28.6139,"f_lon":77.2090,"f_tzone":5.5,"lang":"en"}' \
  -o match.pdf
```

## Frontend

The web UI at `http://localhost:8000` provides:
- Form-based Kundli and Match PDF generation
- Place autocomplete via `/api/geo-search`
- Automatic timezone detection via `/api/timezone`
- Language selection (English / Hindi)

## Testing

```bash
pytest tests/ -v
```

Test files:
- `tests/test_main.py` — Endpoint integration tests
- `tests/test_api_client.py` — API client tests (mocked with respx)
- `tests/test_pdf_generator.py` — PDF generation tests

The `/demo` endpoint uses hardcoded sample data from `demo_data.py` and requires no API key.

## Project Structure

```
smart_kundli/
├── main.py                  # FastAPI app (7 endpoints)
├── api_client.py            # Async API client (81+ parallel calls, 3-phase fetch)
├── pdf_generator.py         # WeasyPrint PDF engine (51 section renderers)
├── match_pdf_generator.py   # Match-making PDF engine
├── config.py                # pydantic-settings configuration
├── models.py                # Pydantic v2 models (KundliRequest, MatchRequest, etc.)
├── demo_data.py             # Sample data for /demo endpoint
├── start.bat                # Windows startup script (sets PATH + runs uvicorn)
├── sections/                # Section renderers (51 files, data -> HTML)
│   ├── __init__.py          # Locale dicts, sign/planet mappings
│   ├── cover.py
│   ├── birth_summary.py
│   ├── panchang.py
│   ├── chart.py
│   ├── planets.py
│   ├── houses.py
│   ├── dasha.py
│   ├── ashtakvarga.py
│   ├── numerology.py
│   ├── lalkitab.py
│   ├── biorhythm.py
│   ├── yogas.py
│   ├── matching.py          # Match-making section renderer
│   └── ... (51 total)
├── templates/               # Jinja2 HTML templates + CSS (52 files)
│   ├── base.html
│   ├── styles.css
│   ├── cover.html
│   ├── matching.html
│   └── ... (52 total)
├── static/                  # Frontend UI
│   ├── index.html           # Main form page
│   ├── form.js              # Form logic & API calls
│   └── form.css             # Styling
├── tests/
│   ├── test_main.py
│   ├── test_api_client.py
│   └── test_pdf_generator.py
├── .env / .env.example
├── requirements.txt
├── CLAUDE.md
└── README.md
```

## Adding a New Section

1. Create `templates/new_section.html` with Jinja2 template
2. Create `sections/new_section.py` with a `render_new_section(data, lang)` function
3. Add the renderer to `SECTION_RENDERERS` list in `pdf_generator.py`
4. Add locale strings to `LOCALES` dict in `sections/__init__.py`
5. Claim the section in `TOC_CHAPTERS` (`sections/__init__.py`) so the Table of Contents lists it — or add it to `UNLISTED_SECTIONS` in `tests/test_pdf_generator.py` if it's front/back matter. The guard tests there fail until you do.

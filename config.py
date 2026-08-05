from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    astro_api_base_url: str = "https://json.astrologyapi.com/v1"
    astro_api_key: str
    astro_api_timeout: int = 30
    astro_api_max_retries: int = 5
    anthropic_api_key: str = ""
    default_lang: str = "hi"
    log_level: str = "INFO"

    author_name: str = ""
    author_title: str = ""
    cta_consult_url: str = ""
    cta_pooja_url: str = ""
    cta_rudraksha_url: str = ""
    brand_footer_enabled: bool = False
    brand_footer_name: str = ""
    brand_footer_url: str = ""
    brand_footer_phone: str = ""

    # The second brand, selected per request via KundliRequest.kundli_type="bloomx".
    # See branding.py, which resolves one of these two sets into a Brand profile.
    # Unlike the Batraa block above these carry real defaults rather than "", so a
    # Bloomx report renders correctly even before .env is populated.
    bloomx_author_name: str = "https://bloomxsolutions.com/"
    bloomx_author_title: str = "Astrologer"
    bloomx_cta_consult_url: str = "https://bloomxsolutions.com/"
    bloomx_cta_pooja_url: str = "https://bloomxsolutions.com/"
    bloomx_cta_rudraksha_url: str = "https://bloomxsolutions.com/"
    bloomx_brand_footer_enabled: bool = True
    bloomx_brand_footer_name: str = "The Bloomx Solutions"
    bloomx_brand_footer_url: str = "https://bloomxsolutions.com/"
    bloomx_brand_footer_phone: str = "+91-7000190457"
    bloomx_cover_image: str = "bloomx_kundli_cover.png"
    bloomx_logo_image: str = "bloomx_logo_dark.png"

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    kundli_price_paise: int = 9900
    payment_currency: str = "INR"
    allow_free_generation: bool = False
    # When False, the paid form/Razorpay flow records the order + notifies Pabbly but does
    # NOT generate the PDF inline — generation is deferred to the sheet_orders DB worker.
    # Prevents double-generation once the order lands in sheet_orders. Reversible via env.
    inline_generation_enabled: bool = True
    use_haiku_for_translation: bool = True
    # Cost optimization: route formulaic narrative batches (planets, numerology)
    # to cheaper Haiku 4.5. Kill-switch: set False to revert ALL narratives to Sonnet.
    use_haiku_for_simple_narratives: bool = True
    api_concurrency: int = 10
    narrative_concurrency: int = 5
    # Max kundli PDFs rendered concurrently. Bursts of simultaneous paid orders
    # queue on this gate so they can't starve the shared API semaphore / OOM the
    # box. See DEPLOYMENT.md §4.1 (5 => ~2.5 GB peak on the 6 GB box).
    generation_concurrency: int = 5

    google_drive_folder_id: str = ""
    # Amount-based routing: sheet orders with order_total_amount above
    # drive_premium_amount_threshold archive here instead of google_drive_folder_id.
    # Empty => routing disabled, everything goes to google_drive_folder_id.
    google_drive_folder_id_premium: str = ""
    drive_premium_amount_threshold: int = 499
    google_oauth_credentials_path: str = "oauth_credentials.json"
    google_token_path: str = "token.json"
    # Full contents of token.json as a string. token.json is excluded from git
    # (.gitignore) AND from the built image (.dockerignore), so on hosts without a
    # file mount (e.g. compose-based Coolify) set this env var to the authorized-user
    # JSON and the app materializes the file at load time.
    google_token_json: str = ""
    drive_archive_enabled: bool = True
    # Per-attempt socket timeout (seconds) for Drive uploads. The underlying
    # httplib2 default (~60s) was killing legitimately-slow uploads from the
    # container's limited egress to Google.
    drive_upload_timeout_seconds: int = 180
    # When a Drive upload ultimately fails, write the paid PDF here so it is
    # recoverable from disk instead of lost. Empty = disabled.
    drive_recovery_dir: str = "recovery"
    generation_timeout_seconds: int = 600
    admin_key: str = ""

    # Standalone sheet_orders sweeper (run: python run_sweeper.py as a SEPARATE single
    # process). sheet_sweeper_enabled is a kill switch for the 24/7 loop; disabling it
    # idles the loop without code changes, but the value is read at import (see `settings`
    # at the bottom of this file), so the process must be restarted — in a container,
    # RECREATED, since `docker restart` keeps the old env. sheet_sweep_interval_seconds is
    # the poll cadence between drains. POST /admin/process-sheet-orders is unaffected.
    sheet_sweeper_enabled: bool = True
    sheet_sweep_interval_seconds: int = 60
    # Liveness heartbeat: the sweeper touches this file after every tick and every
    # processed order, so a container healthcheck can flag a hung/dead sweeper by the
    # file's age. Empty = disabled (local dev).
    sweeper_heartbeat_file: str = ""

    # Where the SQLite narrative cache lives. Empty = narrative_cache.db next to the
    # code (local dev). In containers point it INSIDE a mounted volume DIRECTORY
    # (e.g. /app/data/narrative_cache.db) — mounting a named volume directly onto the
    # .db file path creates a directory and silently disables the cache.
    narrative_cache_path: str = ""

    # Master switch for decorative section artwork in the kundli PDF. When false, the
    # divider pages, the offer banner and the planet deity art are dropped; only the
    # opening front-page image survives. Charts (inline SVG + API chart images) and the
    # brand logo are unaffected — see pdf_logo_enabled and filler_images_enabled.
    pdf_images_enabled: bool = True

    # The brand logo is independent of the divider/deity artwork: it stays on when
    # pdf_images_enabled is false so the cover, author's note, front matter and TOC
    # keep their signature block.
    pdf_logo_enabled: bool = True

    # Post-generation filler images: overlay a promotional image into any page
    # (after filler_skip_pages) whose bottom empty space exceeds filler_gap_threshold.
    # Capped at filler_max_images placements per report.
    filler_images_enabled: bool = True
    filler_gap_threshold: float = 0.40
    filler_skip_pages: int = 15
    filler_max_images: int = 3

    # Pabbly Connect webhook — POST a payment-success payload for downstream
    # automation (WhatsApp, CRM, sheets). Empty = integration disabled.
    pabbly_webhook_url: str = ""

    # Supabase (Postgres) order/payment tracking. Best-effort audit layer — a
    # failure here never blocks payment or PDF generation. Disabled unless both
    # the URL and the service_role key are set. The service_role key bypasses
    # RLS and must stay server-side only — never expose it to the frontend.
    supabase_url: str = ""            # https://<ref>.supabase.co
    supabase_service_key: str = ""    # service_role secret
    supabase_table: str = "kundli_orders"

    # Sheet-driven kundli generation. The worker (POST /admin/process-sheet-orders) reads
    # SUCCESSFUL rows from this table, generates each PDF, and archives it to Drive. Retries a
    # failed row until kundli_attempts hits the cap, then parks it as 'failed_permanent'.
    sheet_orders_table: str = "sheet_orders"
    sheet_orders_kundli_max_attempts: int = 3

    # Credit gating for the sheet sweeper: generate only while the astrologer has credits, and
    # spend one per delivered PDF (credits_repo.py + credits_schema.sql). The astrologer is
    # resolved at runtime (the single is_active row in `astrologers`), so there is no id to
    # configure. false = unmetered generation, the pre-credit behaviour — the rollback switch
    # if the gate ever wrongly blocks production. No rebuild needed, but like every setting
    # here it is read once at import, so it takes effect only on a sweeper recreate.
    credit_check_enabled: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
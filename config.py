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
    brand_footer_enabled: bool = False
    brand_footer_name: str = ""
    brand_footer_url: str = ""
    brand_footer_phone: str = ""

    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    kundli_price_paise: int = 9900
    payment_currency: str = "INR"
    allow_free_generation: bool = False
    use_haiku_for_translation: bool = True
    # Cost optimization: route formulaic narrative batches (planets, numerology)
    # to cheaper Haiku 4.5. Kill-switch: set False to revert ALL narratives to Sonnet.
    use_haiku_for_simple_narratives: bool = True
    api_concurrency: int = 10
    narrative_concurrency: int = 5

    google_drive_folder_id: str = ""
    google_oauth_credentials_path: str = "oauth_credentials.json"
    google_token_path: str = "token.json"
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

    # Post-generation filler images: overlay a promotional image into any page
    # (after filler_skip_pages) whose bottom empty space exceeds filler_gap_threshold.
    filler_images_enabled: bool = True
    filler_gap_threshold: float = 0.40
    filler_skip_pages: int = 15

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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
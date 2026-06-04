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
    kundli_price_paise: int = 9900
    payment_currency: str = "INR"
    allow_free_generation: bool = False
    use_haiku_for_translation: bool = True
    api_concurrency: int = 10
    narrative_concurrency: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[2] == backend/
_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "StockScope API"
    app_env: str = "dev"
    app_debug: bool = True

    market_data_provider: str = "yfinance"
    finnhub_api_key: str = ""
    alpha_vantage_api_key: str = ""

    # Comma-separated origins for browser access to the API (Next.js dev server).
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Market movers: cache full universe snapshot in memory (see snapshot_cache).
    movers_cache_enabled: bool = True
    movers_cache_ttl_intraday_seconds: int = 60
    movers_cache_ttl_previous_day_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
    )


settings = Settings()

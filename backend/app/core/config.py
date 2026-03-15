"""Core configuration module."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "Polymarket AI Team"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/polymarket_ai"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM / OpenRouter
    openrouter_api_key: str = ""
    openrouter_api_key_backup: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "nvidia/nemotron-3-super-120b-a12b:free"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2048
    llm_timeout: int = 60

    # Search APIs (for real-time data)
    serper_api_key: str = ""
    news_api_key: str = ""

    # Polymarket APIs
    gamma_api_url: str = "https://gamma-api.polymarket.com"
    data_api_url: str = "https://data-api.polymarket.com"
    clob_api_url: str = "https://clob.polymarket.com"

    # Trading / Survival Protocol
    starting_capital: float = 500.0
    currency_symbol: str = "₹"
    max_trade_size: float = 30.0
    max_open_trades: int = 5
    min_edge: float = 0.08
    emergency_balance: float = 350.0
    stop_balance: float = 300.0

    # Scheduler
    scan_interval_minutes: int = 30
    resolution_check_interval_minutes: int = 60

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()

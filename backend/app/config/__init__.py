"""Runtime settings loaded from environment variables.

All secrets come from here. ``.env`` is never committed; see ``.env.example``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    log_level: str = "INFO"

    market_data_provider: str = "yfinance"
    market_data_cache_dir: Path = Path("./data/cache")

    bloomberg_enabled: bool = False
    bloomberg_host: str = "localhost"
    bloomberg_port: int = 8194

    tiingo_api_key: str | None = None
    fmp_api_key: str | None = None

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

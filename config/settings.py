"""
Centralized application settings.

All runtime parameters flow through a single Pydantic settings object so the twin
can be reconfigured per-environment (dev / staging / prod) without touching code.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent


class GroqSettings(BaseSettings):
    api_key: str = Field(default="", alias="GROQ_API_KEY")
    model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    timeout: int = Field(default=30, alias="GROQ_TIMEOUT")
    max_tokens: int = Field(default=2048, alias="GROQ_MAX_TOKENS")
    temperature: float = 0.2

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class DuckDBSettings(BaseSettings):
    path: Path = Field(default=ROOT_DIR / "data" / "warehouse.duckdb", alias="DUCKDB_PATH")
    threads: int = Field(default=4, alias="DUCKDB_THREADS")
    memory_limit: str = Field(default="4GB", alias="DUCKDB_MEMORY_LIMIT")
    read_only: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class LakeSettings(BaseSettings):
    bronze: Path = Field(default=ROOT_DIR / "data" / "bronze", alias="LAKE_BRONZE")
    silver: Path = Field(default=ROOT_DIR / "data" / "silver", alias="LAKE_SILVER")
    gold: Path = Field(default=ROOT_DIR / "data" / "gold", alias="LAKE_GOLD")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class TwinSettings(BaseSettings):
    env: str = Field(default="development", alias="TWIN_ENV")
    timezone: str = Field(default="America/Sao_Paulo", alias="TWIN_TIMEZONE")
    tick_seconds: int = Field(default=60, alias="TWIN_TICK_SECONDS")
    horizon_days: int = Field(default=14, alias="TWIN_HORIZON_DAYS")
    light_seed: bool = Field(default=False, alias="TWIN_LIGHT_SEED")
    seed_history_days: int = Field(default=60, alias="TWIN_SEED_HISTORY_DAYS")
    seed_n_skus: int = Field(default=240, alias="TWIN_SEED_N_SKUS")

    # Operational thresholds
    stockout_threshold: float = 0.02      # 2% of SKUs out → critical
    service_level_target: float = 0.985   # 98.5% target service level
    reorder_lead_time_days: int = 3
    safety_stock_multiplier: float = 1.65

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AppSettings(BaseSettings):
    name: str = "Gêmeo Digital de Varejo"
    version: str = "1.1.0"
    tagline: str = "Operational Intelligence · Supply Chain Tower"
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_path: Path = Field(default=ROOT_DIR / "logs" / "twin.log", alias="LOG_PATH")

    groq: GroqSettings = GroqSettings()
    duckdb: DuckDBSettings = DuckDBSettings()
    lake: LakeSettings = LakeSettings()
    twin: TwinSettings = TwinSettings()

    root: Path = ROOT_DIR

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def _load() -> AppSettings:
    return AppSettings()


settings: AppSettings = _load()

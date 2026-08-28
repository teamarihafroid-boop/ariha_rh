from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    database_url: str = "postgresql+psycopg://ariha:ariha_dev_pw@localhost:5433/ariha_dev"
    redis_url: str = "redis://localhost:6379/0"
    session_secret: str = "dev-only-change-me"
    cookie_secure: bool = False
    session_idle_ttl_seconds: int = 60 * 60 * 12
    session_absolute_ttl_seconds: int = 60 * 60 * 24 * 7
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()

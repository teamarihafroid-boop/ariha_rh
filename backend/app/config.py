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
    storage_backend: str = "local"
    storage_local_dir: str = "var/uploads"
    # S3-compatible object storage (e.g. Cloudflare R2) — required when
    # storage_backend=s3. See TECHNICAL_DECISIONS.md §7.
    storage_s3_bucket: str | None = None
    storage_s3_endpoint_url: str | None = None
    storage_s3_access_key_id: str | None = None
    storage_s3_secret_access_key: str | None = None
    storage_s3_region: str = "auto"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash"


@lru_cache
def get_settings() -> Settings:
    return Settings()

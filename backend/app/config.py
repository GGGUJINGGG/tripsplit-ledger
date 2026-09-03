from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent


def _use_psycopg_driver(url: str) -> str:
    """Normalize a bare postgresql:// URL to use the psycopg3 driver.

    Managed Postgres add-ons (Railway, Render, etc.) hand out plain
    postgresql:// connection strings, but this app's SQLAlchemy engine
    needs the +psycopg driver segment. Rewriting it here means the
    platform's auto-generated DATABASE_URL can be used directly instead
    of asking users to hand-edit it.
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class Settings(BaseSettings):
    database_url: str
    # Only needed to run the backend test suite locally/in CI — a
    # deployed instance never sets this.
    test_database_url: Optional[str] = None
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    # Comma-separated list of origins allowed to call this API.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url", "test_database_url")
    @classmethod
    def normalize_database_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return _use_psycopg_driver(value)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
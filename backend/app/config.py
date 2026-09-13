"""Environment-backed application settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_frontend_origins(value: str | None) -> list[str]:
    """Parse one or more comma-separated browser origins safely."""

    origins = [
        origin.strip().rstrip("/")
        for origin in (value or "").split(",")
        if origin.strip()
    ]
    if "*" in origins:
        raise ValueError(
            "FRONTEND_ORIGIN must contain explicit origins; wildcard origins are not supported."
        )
    return origins or ["http://localhost:5173"]


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and .env."""

    database_url: str = ""
    groq_api_key: str | None = None
    groq_model: str | None = None
    frontend_origin: str = "http://localhost:5173"
    app_version: str = "1.0.0"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one cached settings instance for the process."""

    return Settings()

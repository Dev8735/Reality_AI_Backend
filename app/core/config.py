"""Application settings and configuration loading via Pydantic BaseSettings."""

import sys
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL connection string (e.g. postgresql://user:pass@localhost:5432/dbname)",
    )
    SECRET_KEY: str = Field(
        ...,
        description="Secret key used for signing JWT tokens",
    )

    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    PLACEHOLDER_MODE: bool = Field(
        default=True,
        description="When True, POST /chat returns mock replies instead of invoking AI model",
    )


try:
    settings = Settings()
except Exception as e:
    sys.stderr.write(
        f"\n[CRITICAL ERROR] Failed to load backend configuration:\n{e}\n"
        f"Please verify DATABASE_URL and SECRET_KEY are correctly set in your environment or .env file.\n\n"
    )
    sys.exit(1)

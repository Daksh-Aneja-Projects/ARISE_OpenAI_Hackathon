"""
Application configuration using Pydantic Settings.
Loads from .env file and environment variables.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os


class Settings(BaseSettings):
    """Global application settings."""

    # App
    APP_NAME: str = "ARISE — Autonomous RFP Intelligence and Sales Engine"
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./arise.db"

    # LLM - OpenAI
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"
    LLM_FAST_MODEL: str = "gpt-4o-mini"

    # Auth Configuration
    JWT_SECRET: str = (
        ""  # REQUIRED — must be set in .env or environment. No default for security.
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # Storage
    UPLOAD_DIR: str = "../knowledge_base"
    MAX_UPLOAD_SIZE_MB: int = 100

    # Default hourly rates (USD) — override via .env or KB rate card upload
    # Priority: KB uploaded rate card > user_context rates > these defaults
    DEFAULT_RATE_ONSHORE_USD: int = 120  # $/hr onshore
    DEFAULT_RATE_NEARSHORE_USD: int = 90  # $/hr nearshore
    DEFAULT_RATE_OFFSHORE_USD: int = 30  # $/hr offshore

    # Org chart config — path to a JSON file with custom org tree
    # If set and file exists, overrides the built-in template.
    # Example: ORG_CONFIG_FILE=../knowledge_base/org_config.json
    ORG_CONFIG_FILE: str = ""

    # ── Celery (optional — for horizontal agent scaling) ───────────
    # Dev: memory:// (no Redis needed)
    # Prod: redis://localhost:6379/0
    CELERY_BROKER_URL: str = "memory://"
    CELERY_RESULT_BACKEND: str = "cache+memory://"

    # ── pgvector (optional — for persistent multi-process RAG) ─────
    # When set, RAG uses PostgreSQL+pgvector instead of file cache.
    # Example: postgresql+asyncpg://user:pass@localhost/arise
    PGVECTOR_URL: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

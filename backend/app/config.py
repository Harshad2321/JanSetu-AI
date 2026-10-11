"""
JanSetu AI — Application Configuration & Settings.

Centralizes configuration for:
- Environment mode (development / production)
- Database connection URL (SQLite for local college PoC)
- Secure local storage directory for sanitized images (non-public)
- CORS permitted origins
- Groq model selection and API credentials
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application runtime settings with environment variable fallbacks."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = Field(default="development", description="Runtime environment")
    DATABASE_URL: str = Field(
        default="sqlite:///./data/jansetu.db",
        description="SQLAlchemy database connection URI",
    )
    # Database connection pool settings for hosted PostgreSQL
    DB_POOL_SIZE: int = Field(default=5, description="PostgreSQL connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="PostgreSQL connection pool max overflow")
    DB_POOL_TIMEOUT: int = Field(default=30, description="PostgreSQL connection pool timeout in seconds")
    DB_POOL_RECYCLE: int = Field(default=300, description="PostgreSQL connection pool recycle interval in seconds")

    # Image Storage Settings
    STORAGE_PROVIDER: str = Field(
        default="local",
        description="Active storage provider ('local' or 'supabase')",
    )
    STORAGE_DIR: str = Field(
        default="./data/uploads",
        description="Local filesystem directory for private sanitized image storage",
    )
    SUPABASE_URL: str | None = Field(
        default=None,
        description="Supabase project URL for hosted storage",
    )
    SUPABASE_SERVICE_ROLE_KEY: str | None = Field(
        default=None,
        description="Supabase Service Role Key for server-side storage access (never expose to client)",
    )
    SUPABASE_STORAGE_BUCKET: str = Field(
        default="jansetu-evidence",
        description="Private Supabase storage bucket name for sanitized incident photographs",
    )
    SUPABASE_SIGNED_URL_EXPIRY_SECONDS: int = Field(
        default=900,
        description="Lifetime of backend-generated short-lived signed URLs in seconds (15 minutes)",
    )

    # Security, Demo & Limits
    DEMO_MODE: bool = Field(
        default=True,
        description="Allow demonstration simulations and reset endpoints",
    )
    MAX_UPLOAD_SIZE_MB: int = Field(
        default=10,
        description="Maximum accepted photograph upload size in megabytes",
    )

    CORS_ALLOWED_ORIGINS_RAW: str = Field(
        default="http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175,http://127.0.0.1:3000",
        alias="CORS_ALLOWED_ORIGINS",
        description="Comma-delimited permitted CORS origins",
    )
    GROQ_API_KEY: str | None = Field(
        default=None,
        description="Optional Groq API key for vision multimodal model",
    )
    GROQ_MODEL: str = Field(
        default="qwen/qwen3.8-27b",
        description="Groq vision model identifier",
    )

    @property
    def normalized_database_url(self) -> str:
        """
        Normalize database URL for SQLAlchemy 2.0+ compatibility using psycopg2.
        Supabase and cloud providers often supply 'postgres://' or 'postgresql://'
        which must map to 'postgresql+psycopg2://' when using psycopg2-binary.
        """
        url = self.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        return url

    @property
    def is_sqlite(self) -> bool:
        """Check if active database is SQLite."""
        return self.normalized_database_url.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        """Check if active database is PostgreSQL."""
        return self.normalized_database_url.startswith("postgresql")

    @property
    def cors_origins(self) -> List[str]:
        """Parse raw comma-separated CORS origins into a stripped list."""
        if not self.CORS_ALLOWED_ORIGINS_RAW:
            return ["http://localhost:5173", "http://localhost:3000"]
        return [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS_RAW.split(",")
            if origin.strip()
        ]

    def ensure_directories(self) -> None:
        """Create storage and data directories if using local persistence."""
        # Ensure database directory exists if using local sqlite
        if self.is_sqlite and self.normalized_database_url.startswith("sqlite:///"):
            db_path_str = self.normalized_database_url.replace("sqlite:///", "")
            db_path = Path(db_path_str)
            if db_path.parent and str(db_path.parent) != ".":
                db_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure image upload storage directory exists if using local storage
        if self.STORAGE_PROVIDER.lower() == "local":
            storage_path = Path(self.STORAGE_DIR)
            storage_path.mkdir(parents=True, exist_ok=True)


# Global settings singleton
settings = Settings()

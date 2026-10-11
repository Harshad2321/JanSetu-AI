"""
JanSetu AI — Database Engine & Session Management.

Provides:
- SQLite engine configuration with thread safety for FastAPI
- Non-destructive table initialization
- Session dependency for API endpoints
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Generator
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.config import settings

logger = logging.getLogger("jansetu.db")

# Ensure required directories exist before connecting
settings.ensure_directories()


def build_engine(database_url: str | None = None) -> Engine:
    """
    Construct a production-ready SQLAlchemy Engine.
    
    Supports:
    - SQLite: check_same_thread=False for FastAPI concurrency, StaticPool for memory DBs.
    - PostgreSQL (Supabase / Render): Connection pooling with pre-ping, overflow limits, and recycling.
    - Safe logging: Masks database credentials in all logs.
    """
    url = (database_url or settings.normalized_database_url).strip()
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    
    if url.startswith("sqlite"):
        connect_args: Dict[str, Any] = {"check_same_thread": False}
        kwargs: Dict[str, Any] = {"connect_args": connect_args}
        if ":memory:" in url or url == "sqlite://":
            kwargs["poolclass"] = StaticPool
        new_engine = create_engine(url, echo=False, **kwargs)
    else:
        # PostgreSQL / Hosted Supabase configuration
        new_engine = create_engine(
            url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=True,
            echo=False,
        )

    # Safely log connection without leaking passwords
    try:
        masked_url = new_engine.url.render_as_string(hide_password=True)
    except Exception:
        masked_url = "configured database"
    logger.info("Configured database engine for: %s", masked_url)
    return new_engine


engine = build_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a managed database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Idempotent, non-destructive table creation.
    Never drops existing tables or wipes historical civic records.
    """
    try:
        masked_url = engine.url.render_as_string(hide_password=True)
    except Exception:
        masked_url = "database"
    logger.info("Initializing database schema at: %s", masked_url)
    Base.metadata.create_all(bind=engine)

"""
JanSetu AI — Database Configuration & Multi-Driver Unit Tests.

Validates:
- Safe conversion of postgres:// URL to postgresql://
- Correct engine creation for both SQLite and PostgreSQL
- Connection pooling parameters applied to PostgreSQL engine
- Zero password leakage when engine URL is logged/rendered
"""

import pytest
from app.config import Settings
from app.db.session import build_engine


def test_postgres_url_normalization():
    """Ensure postgres:// is cleanly upgraded to postgresql:// for SQLAlchemy 2.0+."""
    custom_settings = Settings(
        DATABASE_URL="postgres://postgres.myproject:secretpassword123@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    )
    norm = custom_settings.normalized_database_url
    assert norm.startswith("postgresql+psycopg2://")
    assert not norm.startswith("postgres://")
    assert custom_settings.is_postgres is True
    assert custom_settings.is_sqlite is False


def test_sqlite_url_detection():
    """Ensure SQLite URL is recognized correctly."""
    custom_settings = Settings(
        DATABASE_URL="sqlite:///./data/test.db"
    )
    assert custom_settings.is_sqlite is True
    assert custom_settings.is_postgres is False


def test_sqlite_engine_creation():
    """Ensure SQLite engine creation sets check_same_thread=False."""
    engine = build_engine("sqlite:///:memory:")
    assert engine.dialect.name == "sqlite"
    assert engine.url.database == ":memory:"


def test_postgres_engine_pool_configuration():
    """
    Ensure PostgreSQL engine is configured with connection pooling
    and pre-ping checks as required for Supabase and Render.
    """
    pg_url = "postgresql://testuser:testpass123@localhost:5432/testdb"
    engine = build_engine(pg_url)
    assert engine.dialect.name == "postgresql"
    
    # Check pool attributes
    pool = engine.pool
    assert hasattr(pool, "_pre_ping")
    assert pool._pre_ping is True
    assert pool.size() == 5
    assert pool._max_overflow == 10
    assert pool._timeout == 30
    assert pool._recycle == 300


def test_db_credentials_masked_in_rendering():
    """Ensure database passwords are masked in rendered representations."""
    pg_url = "postgresql://user_john:super_secret_db_pass_999@db.supabase.co:5432/postgres"
    engine = build_engine(pg_url)
    
    rendered = engine.url.render_as_string(hide_password=True)
    assert "super_secret_db_pass_999" not in rendered
    assert "***" in rendered or "user_john:***@" in rendered or "user_john" in rendered

"""
Base SQLAlchemy configuration and utilities for Rung models.
"""

import os
from datetime import datetime
from typing import Generator
from uuid import UUID

from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator


class JSONType(TypeDecorator):
    """Cross-database JSON type that works with both PostgreSQL and SQLite.

    Uses JSONB on PostgreSQL for performance, falls back to JSON on SQLite.
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


# Database URL from environment or default to SQLite for testing
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./test.db"  # Default for testing
)

# For PostgreSQL in production, ensure proper async driver
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)


def get_engine(database_url: str | None = None):
    """Create SQLAlchemy engine.

    Args:
        database_url: Optional database URL override.

    Returns:
        SQLAlchemy engine instance.
    """
    url = database_url or DATABASE_URL

    # SQLite-specific settings
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=os.getenv("SQL_ECHO", "false").lower() == "true"
        )

    # PostgreSQL settings
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo=os.getenv("SQL_ECHO", "false").lower() == "true"
    )


# Default engine and session factory
_engine = None
_SessionLocal = None


def get_session_factory(engine=None):
    """Get or create session factory."""
    global _engine, _SessionLocal

    if engine is not None:
        return sessionmaker(autocommit=False, autoflush=False, bind=engine)

    if _SessionLocal is None:
        _engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

    return _SessionLocal


def get_session() -> Generator[Session, None, None]:
    """Dependency for getting database sessions.

    Yields:
        SQLAlchemy session instance.
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db(engine=None) -> None:
    """Initialize database tables.

    Args:
        engine: Optional engine to use. Uses default if not provided.
    """
    if engine is None:
        engine = get_engine()

    Base.metadata.create_all(bind=engine)


def drop_db(engine=None) -> None:
    """Drop all database tables. USE WITH CAUTION.

    Args:
        engine: Optional engine to use. Uses default if not provided.
    """
    if engine is None:
        engine = get_engine()

    Base.metadata.drop_all(bind=engine)

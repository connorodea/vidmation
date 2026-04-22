"""Database engine setup and session factory."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from aividio.config.settings import get_settings
from aividio.models.base import Base


@lru_cache
def get_engine() -> Engine:
    """Create and cache the database engine."""
    settings = get_settings()
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(
        settings.database_url,
        connect_args=connect_args,
        echo=False,
    )


def get_session() -> Session:
    """Create a new database session."""
    engine = get_engine()
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def init_db() -> None:
    """Create all tables. Use for development; prefer Alembic migrations in production."""
    engine = get_engine()
    Base.metadata.create_all(engine)

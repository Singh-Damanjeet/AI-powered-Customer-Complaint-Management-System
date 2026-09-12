"""SQLAlchemy engine and session helpers."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create the SQLAlchemy engine only when database access is requested."""

    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    return create_engine(database_url, pool_pre_ping=True)


def get_session_factory() -> sessionmaker[Session]:
    """Return a session factory bound to the configured engine."""

    return sessionmaker(
        bind=get_engine(),
        autocommit=False,
        autoflush=False,
    )


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for dependency-injected API handlers."""

    database = get_session_factory()()
    try:
        yield database
    finally:
        database.close()

"""SQLAlchemy engine and session helpers."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, text
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


def check_database_connection() -> None:
    """Raise if the configured database cannot execute a trivial query."""

    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))


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

"""SQLAlchemy types shared by persistence models."""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB


# Use JSONB in PostgreSQL while keeping repository tests portable to SQLite.
JSONBType = JSON().with_variant(JSONB(), "postgresql")

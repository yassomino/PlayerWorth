"""Explicit engine/session factories suitable for CLI and future request lifecycles."""

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker


def create_db_engine(url: str | None = None) -> Engine:
    raw = url or os.environ.get("DATABASE_URL")
    if not raw:
        raise ValueError("Set DATABASE_URL to a PostgreSQL connection string")
    parsed = make_url(raw)
    if parsed.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise ValueError("Only PostgreSQL with psycopg is supported")
    return create_engine(parsed.set(drivername="postgresql+psycopg"), pool_pre_ping=True)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Commit on success, roll back on error, and always close the session."""
    with factory.begin() as session:
        yield session

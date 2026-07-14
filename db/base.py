"""Shared SQLAlchemy declarative base, engine, and session factory.

Lives outside the pipeline module map (specs/04-architecture.md §5's 17 named
modules) deliberately, not by oversight: `eval/` has a blanket ban on
importing any other first-party module (tests/architecture/import_graph.py's
FORBIDDEN_IMPORTS), and `eval/` is one of this schema's five owning modules
(specs/05-data-model.md's Owner column). A shared persistence layer inside a
pipeline module (e.g. config/) would make eval/'s own models unable to import
it. db/ sits below the module graph instead, the same category tests/ and
tools/ already occupy — see .scratch/data-foundation/issues/
01-postgres-schema-migration.md for the full reasoning.
"""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Declarative base every owning module's models inherit from."""


def get_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine.

    `database_url` defaults to the `DATABASE_URL` environment variable —
    never hardcoded, and never eagerly connected here (constructing an
    Engine does not open a connection until first use).
    """
    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set and no database_url was provided"
        )
    return create_engine(url)


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a session factory bound to the given engine."""
    return sessionmaker(bind=engine)

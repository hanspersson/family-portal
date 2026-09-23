"""SQLAlchemy engine/session setup, scoped to the Flask app.

The engine and sessionmaker are built once per app instance (in
``init_engine``, called from ``create_app``) and stashed on
``app.extensions``, rather than as module-level globals -- this is what
lets tests spin up a fresh app with its own throwaway database without
any monkeypatching. Each request gets its own SQLAlchemy session, opened
lazily on first use and closed automatically when the request ends.
"""

from __future__ import annotations

from flask import Flask, current_app, g
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def init_engine(app: Flask) -> None:
    engine = create_engine(
        app.config["DATABASE_URL"],
        connect_args={"check_same_thread": False},
    )
    app.extensions["db_engine"] = engine
    app.extensions["db_sessionmaker"] = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app.teardown_appcontext(_close_db)


def get_engine() -> Engine:
    return current_app.extensions["db_engine"]


def get_db() -> Session:
    """Return this request's SQLAlchemy session, creating it on first use."""
    if "db" not in g:
        g.db = current_app.extensions["db_sessionmaker"]()
    return g.db


def _close_db(exception: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app: Flask) -> None:
    """Create all tables. Safe to call repeatedly."""
    from family_portal import models  # noqa: F401  (ensure models are registered)

    Base.metadata.create_all(bind=app.extensions["db_engine"])

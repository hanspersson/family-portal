"""Family Portal: a self-hosted Flask app for a household's shared
calendar, wiki, and file storage."""

from __future__ import annotations

from pathlib import Path

from flask import Flask

from family_portal.config import Config
from family_portal.database import init_db, init_engine
from family_portal.formatting import register_filters

PACKAGE_DIR = Path(__file__).resolve().parent


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(PACKAGE_DIR / "templates"),
        static_folder=str(PACKAGE_DIR / "static"),
    )
    app.config.from_object(Config())
    if config_overrides:
        app.config.update(config_overrides)

    register_filters(app)
    init_engine(app)
    with app.app_context():
        init_db(app)

    from family_portal.blueprints import auth, calendar, dashboard, files, wiki

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(calendar.bp)
    app.register_blueprint(wiki.bp)
    app.register_blueprint(files.bp)

    return app

"""Application configuration.

Settings are read from the environment (and a ``.env`` file in the
project root, if present) with a ``FAMILY_PORTAL_`` prefix, e.g.
``FAMILY_PORTAL_SECRET_KEY=...``. Flask picks up the uppercase
attributes of a ``Config`` instance via ``app.config.from_object``.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")


class Config:
    def __init__(self) -> None:
        # Signs session cookies. MUST be overridden with a random, secret
        # value in any real deployment (e.g. `openssl rand -hex 32`).
        self.SECRET_KEY = os.environ.get(
            "FAMILY_PORTAL_SECRET_KEY", "dev-insecure-secret-change-me"
        )

        data_dir = BASE_DIR / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.DATABASE_PATH = Path(
            os.environ.get("FAMILY_PORTAL_DATABASE_PATH", data_dir / "family_portal.db")
        )
        self.DATABASE_URL = f"sqlite:///{self.DATABASE_PATH}"

        uploads_dir = Path(os.environ.get("FAMILY_PORTAL_UPLOADS_DIR", BASE_DIR / "uploads"))
        uploads_dir.mkdir(parents=True, exist_ok=True)
        self.UPLOADS_DIR = uploads_dir

        # How long a login stays valid. Default: 30 days.
        self.PERMANENT_SESSION_LIFETIME = timedelta(
            seconds=int(os.environ.get("FAMILY_PORTAL_SESSION_MAX_AGE", 60 * 60 * 24 * 30))
        )

        # Flask enforces this itself (413 response) -- default: 250 MB.
        self.MAX_CONTENT_LENGTH = int(
            os.environ.get("FAMILY_PORTAL_MAX_UPLOAD_SIZE", 250 * 1024 * 1024)
        )

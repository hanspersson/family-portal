from __future__ import annotations

from collections.abc import Iterator

import pytest
from flask.testing import FlaskClient

from family_portal import create_app


@pytest.fixture()
def client(tmp_path) -> Iterator[FlaskClient]:
    """A Flask test client wired to a throwaway SQLite DB and uploads dir
    per test."""
    db_path = tmp_path / "test.db"
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()

    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": f"sqlite:///{db_path}",
            "UPLOADS_DIR": uploads_dir,
            "SECRET_KEY": "test-secret",
        }
    )

    with app.test_client() as test_client:
        yield test_client

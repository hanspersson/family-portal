"""WSGI entry point.

Production (e.g. behind a reverse proxy on your home server), with gunicorn:

    uv run gunicorn -w 2 -b 0.0.0.0:8000 family_portal.wsgi:app

Development:

    uv run flask --app family_portal.wsgi --debug run --host 0.0.0.0 --port 8000

or simply:

    uv run family-portal
"""

from __future__ import annotations

from family_portal import create_app

app = create_app()


def run() -> None:
    """Entry point for `uv run family-portal` -- convenient for local use,
    not meant for production (use gunicorn instead, see module docstring)."""
    app.run(host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()

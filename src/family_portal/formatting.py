"""Jinja template filters for displaying stored values.

Timestamps: SQLite has no timezone-aware column type, so SQLAlchemy
stores ``DateTime(timezone=True)`` values with the offset dropped. The
app writes bookkeeping timestamps (``created_at``, ``updated_at``,
``uploaded_at``) as UTC, so they come back as *naive UTC* and must be
converted before display. Calendar events are different: their times
are the wall-clock times a family member typed in, stored and shown
as-is (naive local), and must NOT go through ``localtime``.
"""

from __future__ import annotations

from datetime import datetime, timezone, tzinfo
from zoneinfo import ZoneInfo

from flask import Flask, current_app


def display_tz() -> tzinfo | None:
    """The configured display timezone, or None for the server's own."""
    name = current_app.config.get("TIMEZONE")
    return ZoneInfo(name) if name else None


def local_now() -> datetime:
    """Current wall-clock time in the display timezone, naive -- the same
    form calendar events are stored in, so the two can be compared."""
    return datetime.now(timezone.utc).astimezone(display_tz()).replace(tzinfo=None)


def localtime(value: datetime) -> datetime:
    """Convert a stored UTC timestamp (naive or aware) to display time."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(display_tz())


def filesize(num_bytes: int) -> str:
    """Human-readable size: "20 bytes", "3.4 KB", "1.2 MB" (1 KB = 1024 B)."""
    if num_bytes < 1024:
        return f"{num_bytes} byte{'' if num_bytes == 1 else 's'}"
    size = num_bytes / 1024
    for unit in ("KB", "MB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def register_filters(app: Flask) -> None:
    app.add_template_filter(localtime, "localtime")
    app.add_template_filter(filesize, "filesize")

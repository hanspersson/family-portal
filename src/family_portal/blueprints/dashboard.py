from __future__ import annotations

from datetime import timedelta

from flask import Blueprint, render_template

from family_portal.database import get_db
from family_portal.deps import get_current_user, login_required
from family_portal.formatting import local_now
from family_portal.models import Event, FileItem, WikiPage

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def home():
    user = get_current_user()
    db = get_db()
    # Events are stored as naive local wall-clock times, so compare
    # against local time, not UTC (see formatting.py).
    now = local_now()

    upcoming_events = (
        db.query(Event)
        .filter(
            Event.household_id == user.household_id,
            Event.start_at >= now - timedelta(hours=1),
            Event.start_at <= now + timedelta(days=14),
        )
        .order_by(Event.start_at)
        .limit(8)
        .all()
    )
    recent_pages = (
        db.query(WikiPage)
        .filter(WikiPage.household_id == user.household_id)
        .order_by(WikiPage.updated_at.desc())
        .limit(5)
        .all()
    )
    recent_files = (
        db.query(FileItem)
        .filter(FileItem.household_id == user.household_id)
        .order_by(FileItem.uploaded_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "dashboard.html",
        user=user,
        upcoming_events=upcoming_events,
        recent_pages=recent_pages,
        recent_files=recent_files,
    )

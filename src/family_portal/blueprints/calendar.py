from __future__ import annotations

from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from flask import Blueprint, redirect, render_template, request, url_for

from family_portal.database import get_db
from family_portal.deps import get_current_user, login_required
from family_portal.models import Event

bp = Blueprint("calendar", __name__, url_prefix="/calendar")


def _parse_month(month_str: str | None) -> date:
    if month_str:
        try:
            return datetime.strptime(month_str, "%Y-%m").date().replace(day=1)
        except ValueError:
            pass
    return date.today().replace(day=1)


@bp.route("")
@login_required
def list_events():
    user = get_current_user()
    db = get_db()
    month_start = _parse_month(request.args.get("month"))
    month_end = month_start + relativedelta(months=1)

    events = (
        db.query(Event)
        .filter(
            Event.household_id == user.household_id,
            Event.start_at < month_end,
            Event.end_at >= month_start,
        )
        .order_by(Event.start_at)
        .all()
    )

    prev_month = (month_start - relativedelta(months=1)).strftime("%Y-%m")
    next_month = month_end.strftime("%Y-%m")

    return render_template(
        "calendar.html",
        user=user,
        events=events,
        month_label=month_start.strftime("%B %Y"),
        prev_month=prev_month,
        next_month=next_month,
    )


@bp.route("/new", methods=["POST"])
@login_required
def create_event():
    user = get_current_user()
    db = get_db()
    form = request.form

    start = datetime.fromisoformat(form["start_at"])
    end_at = form.get("end_at")
    end = datetime.fromisoformat(end_at) if end_at else start + timedelta(hours=1)

    event = Event(
        household_id=user.household_id,
        created_by_id=user.id,
        title=form["title"].strip(),
        description=form.get("description", "").strip(),
        location=form.get("location", "").strip(),
        start_at=start,
        end_at=end,
        all_day=bool(form.get("all_day")),
    )
    db.add(event)
    db.commit()
    return redirect(url_for("calendar.list_events", month=start.strftime("%Y-%m")))


@bp.route("/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_event(event_id: int):
    user = get_current_user()
    db = get_db()
    event = db.get(Event, event_id)
    if event is not None and event.household_id == user.household_id:
        db.delete(event)
        db.commit()
    return redirect(url_for("calendar.list_events"))

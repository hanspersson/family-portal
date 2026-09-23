from __future__ import annotations

import re

from flask import Blueprint, abort, redirect, render_template, request, session, url_for

from family_portal.database import get_db
from family_portal.deps import get_current_user, login_required
from family_portal.models import Household, User
from family_portal.security import hash_password, verify_password

bp = Blueprint("auth", __name__)


def _slugify_username(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower()) or "user"


@bp.route("/login", methods=["GET"])
def login_page():
    db = get_db()
    if db.query(User).count() == 0:
        # No family set up yet -- first-run flow creates the household + admin.
        return render_template("setup.html")
    return render_template("login.html")


@bp.route("/setup", methods=["POST"])
def setup():
    db = get_db()
    if db.query(User).count() > 0:
        # Setup already happened; don't let it run twice.
        return redirect(url_for("auth.login_page"))

    form = request.form
    household = Household(name=form["household_name"].strip())
    db.add(household)
    db.flush()

    user = User(
        household_id=household.id,
        username=form["username"].strip().lower(),
        display_name=form["display_name"].strip(),
        password_hash=hash_password(form["password"]),
        is_admin=True,
    )
    db.add(user)
    db.commit()

    session.permanent = True
    session["user_id"] = user.id
    return redirect(url_for("dashboard.home"))


@bp.route("/login", methods=["POST"])
def login():
    db = get_db()
    username = request.form["username"].strip().lower()
    password = request.form["password"]
    next_path = request.form.get("next", "/")

    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(password, user.password_hash):
        return redirect(url_for("auth.login_page", error=1))

    session.permanent = True
    session["user_id"] = user.id

    # Only ever redirect to a same-site path, never an absolute URL, so a
    # crafted `next` value can't send someone off-site after logging in.
    safe_next = next_path if next_path.startswith("/") and not next_path.startswith("//") else "/"
    return redirect(safe_next)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))


@bp.route("/members", methods=["GET"])
@login_required
def members_page():
    user = get_current_user()
    db = get_db()
    members = (
        db.query(User).filter(User.household_id == user.household_id).order_by(User.id).all()
    )
    return render_template("members.html", user=user, members=members)


@bp.route("/members", methods=["POST"])
@login_required
def add_member():
    user = get_current_user()
    if not user.is_admin:
        # Only admins create logins -- otherwise any family member (e.g. a
        # child's account) could mint new accounts, including admin ones.
        abort(403)
    db = get_db()
    form = request.form
    new_user = User(
        household_id=user.household_id,
        username=_slugify_username(form["username"]),
        display_name=form["display_name"].strip(),
        password_hash=hash_password(form["password"]),
        is_admin=bool(form.get("is_admin")),
    )
    db.add(new_user)
    db.commit()
    return redirect(url_for("auth.members_page"))

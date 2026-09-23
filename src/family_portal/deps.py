"""Login helpers: current user lookup and a `login_required` decorator
for view functions (redirects to /login rather than the bare 401 an API
would return, since these are server-rendered pages)."""

from __future__ import annotations

from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from flask import g, redirect, request, session, url_for

from family_portal.database import get_db
from family_portal.models import User

P = ParamSpec("P")
R = TypeVar("R")


def get_current_user() -> User | None:
    """Return the logged-in User for this request, or None. Cached on
    `g` so repeated calls within one request don't re-query the DB."""
    if "user" not in g:
        user_id = session.get("user_id")
        g.user = get_db().get(User, user_id) if user_id is not None else None
    return g.user


def login_required(view: Callable[P, R]) -> Callable[P, R]:
    @wraps(view)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        if get_current_user() is None:
            return redirect(url_for("auth.login_page", next=request.path))  # type: ignore[return-value]
        return view(*args, **kwargs)

    return wrapped

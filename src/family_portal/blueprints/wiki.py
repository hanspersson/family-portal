from __future__ import annotations

import re

import markdown as markdown_lib
import nh3
from flask import Blueprint, abort, redirect, render_template, request, url_for
from sqlalchemy.orm import Session

from family_portal.database import get_db
from family_portal.deps import get_current_user, login_required
from family_portal.models import WikiPage, WikiRevision

bp = Blueprint("wiki", __name__, url_prefix="/wiki")


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "page"


# nh3's default allowlist, plus heading ids (added by the `toc` extension
# so headings can be linked to).
_ALLOWED_ATTRIBUTES = {
    **nh3.ALLOWED_ATTRIBUTES,
    **{h: nh3.ALLOWED_ATTRIBUTES.get(h, set()) | {"id"} for h in ("h1", "h2", "h3", "h4", "h5", "h6")},
}


def _render_markdown(text: str) -> str:
    """Render wiki markdown to HTML that is safe to output unescaped.

    Markdown passes raw HTML through, and the template marks the result
    `| safe`, so without sanitizing any family member could put a
    <script> (or an onerror= handler) on a page that runs in everyone
    else's logged-in browser. nh3 strips scripts, event handlers and
    javascript: URLs while keeping normal formatting.
    """
    html = markdown_lib.markdown(text, extensions=["extra", "sane_lists", "toc"])
    return nh3.clean(html, attributes=_ALLOWED_ATTRIBUTES)


def _unique_slug(db: Session, household_id: int, base_slug: str) -> str:
    slug = base_slug
    suffix = 2
    while (
        db.query(WikiPage)
        .filter(WikiPage.household_id == household_id, WikiPage.slug == slug)
        .first()
        is not None
    ):
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


def _get_page_or_404(db: Session, household_id: int, slug: str) -> WikiPage:
    page = (
        db.query(WikiPage)
        .filter(WikiPage.household_id == household_id, WikiPage.slug == slug)
        .first()
    )
    if page is None:
        abort(404, description="Wiki page not found")
    return page


@bp.route("")
@login_required
def list_pages():
    user = get_current_user()
    db = get_db()
    pages = (
        db.query(WikiPage)
        .filter(WikiPage.household_id == user.household_id)
        .order_by(WikiPage.title)
        .all()
    )
    return render_template("wiki_list.html", user=user, pages=pages)


@bp.route("/new", methods=["GET"])
@login_required
def new_page_form():
    return render_template("wiki_edit.html", user=get_current_user(), page=None)


@bp.route("/new", methods=["POST"])
@login_required
def create_page():
    user = get_current_user()
    db = get_db()
    form = request.form

    slug = _unique_slug(db, user.household_id, _slugify(form["title"]))
    page = WikiPage(
        household_id=user.household_id,
        slug=slug,
        title=form["title"].strip(),
        content_markdown=form.get("content_markdown", ""),
        updated_by_id=user.id,
    )
    db.add(page)
    db.flush()
    db.add(
        WikiRevision(
            page_id=page.id,
            edited_by_id=user.id,
            title=page.title,
            content_markdown=page.content_markdown,
        )
    )
    db.commit()
    return redirect(url_for("wiki.view_page", slug=slug))


@bp.route("/<slug>")
@login_required
def view_page(slug: str):
    user = get_current_user()
    db = get_db()
    page = _get_page_or_404(db, user.household_id, slug)
    return render_template(
        "wiki_page.html", user=user, page=page, content_html=_render_markdown(page.content_markdown)
    )


@bp.route("/<slug>/edit", methods=["GET"])
@login_required
def edit_page_form(slug: str):
    user = get_current_user()
    db = get_db()
    page = _get_page_or_404(db, user.household_id, slug)
    return render_template("wiki_edit.html", user=user, page=page)


@bp.route("/<slug>/edit", methods=["POST"])
@login_required
def edit_page(slug: str):
    user = get_current_user()
    db = get_db()
    page = _get_page_or_404(db, user.household_id, slug)
    form = request.form

    page.title = form["title"].strip()
    page.content_markdown = form.get("content_markdown", "")
    page.updated_by_id = user.id
    db.add(
        WikiRevision(
            page_id=page.id,
            edited_by_id=user.id,
            title=page.title,
            content_markdown=page.content_markdown,
        )
    )
    db.commit()
    return redirect(url_for("wiki.view_page", slug=slug))


@bp.route("/<slug>/history")
@login_required
def page_history(slug: str):
    user = get_current_user()
    db = get_db()
    page = _get_page_or_404(db, user.household_id, slug)
    return render_template("wiki_history.html", user=user, page=page)

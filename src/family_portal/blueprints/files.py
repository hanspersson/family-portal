from __future__ import annotations

import uuid
from pathlib import Path

from flask import Blueprint, abort, current_app, redirect, render_template, request, send_file, url_for

from family_portal.database import get_db
from family_portal.deps import get_current_user, login_required
from family_portal.models import FileItem
from sqlalchemy.orm import Session

bp = Blueprint("files", __name__, url_prefix="/files")


def _get_item_or_404(db: Session, household_id: int, item_id: int) -> FileItem:
    item = db.get(FileItem, item_id)
    if item is None or item.household_id != household_id:
        abort(404, description="File not found")
    return item


@bp.route("")
@login_required
def list_files():
    user = get_current_user()
    db = get_db()
    items = (
        db.query(FileItem)
        .filter(FileItem.household_id == user.household_id)
        .order_by(FileItem.uploaded_at.desc())
        .all()
    )
    return render_template("files.html", user=user, items=items)


@bp.route("/upload", methods=["POST"])
@login_required
def upload_file():
    user = get_current_user()
    db = get_db()

    upload = request.files.get("upload")
    if upload is None or not upload.filename:
        abort(400, description="No file provided")

    # Oversized uploads are already rejected by Flask (413, via
    # MAX_CONTENT_LENGTH) before this view ever runs.
    stored_name = uuid.uuid4().hex
    dest_path = Path(current_app.config["UPLOADS_DIR"]) / stored_name
    upload.save(dest_path)

    item = FileItem(
        household_id=user.household_id,
        uploaded_by_id=user.id,
        stored_name=stored_name,
        original_filename=upload.filename,
        content_type=upload.content_type or "application/octet-stream",
        size_bytes=dest_path.stat().st_size,
        description=request.form.get("description", ""),
    )
    db.add(item)
    db.commit()
    return redirect(url_for("files.list_files"))


@bp.route("/<int:item_id>/download")
@login_required
def download_file(item_id: int):
    user = get_current_user()
    db = get_db()
    item = _get_item_or_404(db, user.household_id, item_id)
    path = Path(current_app.config["UPLOADS_DIR"]) / item.stored_name
    if not path.exists():
        abort(404, description="File missing on disk")
    return send_file(
        path,
        download_name=item.original_filename,
        mimetype=item.content_type,
        as_attachment=True,
    )


@bp.route("/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_file(item_id: int):
    user = get_current_user()
    db = get_db()
    item = _get_item_or_404(db, user.household_id, item_id)
    path = Path(current_app.config["UPLOADS_DIR"]) / item.stored_name
    path.unlink(missing_ok=True)
    db.delete(item)
    db.commit()
    return redirect(url_for("files.list_files"))

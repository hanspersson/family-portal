"""ORM models.

Data model overview
--------------------
- ``Household``: the family unit. Everything else belongs to exactly one
  household. A single-family deployment will just have one row here, but
  keeping it as its own table means the app already supports multiple
  households sharing one server (e.g. extended family, or in-laws) without
  a schema change later.
- ``User``: a family member's login. Belongs to a household.
- ``Event``: a calendar entry, shared with the whole household by default.
- ``WikiPage`` / ``WikiRevision``: a simple markdown wiki with history.
- ``FileItem``: metadata for an uploaded file; the bytes live on disk
  under ``settings.uploads_dir``, named by the row's UUID to avoid
  filename collisions/traversal issues.

Sharing model (v1)
-------------------
Everything is scoped to a household, and every member of a household can
see everything in it -- there is no per-item, per-person ACL yet. That is
the simplest model that satisfies "share between family members", and the
household foreign key on every table is the seam to add finer-grained
sharing (e.g. a ``visible_to`` join table) later without restructuring.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from family_portal.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


class Household(Base):
    __tablename__ = "households"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="household")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"))
    username: Mapped[str] = mapped_column(Text, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    household: Mapped[Household] = relationship(back_populates="users")


class Event(Base):
    """A calendar event, visible to the whole household."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"), index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(Text, default="")

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    all_day: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    created_by: Mapped[User] = relationship()


class WikiPage(Base):
    """A wiki page. Content is the *current* revision; history lives in
    WikiRevision so nothing a family member writes is ever silently lost."""

    __tablename__ = "wiki_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"), index=True)

    slug: Mapped[str] = mapped_column(Text, index=True)
    title: Mapped[str] = mapped_column(Text)
    content_markdown: Mapped[str] = mapped_column(Text, default="")

    updated_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    updated_by: Mapped[User] = relationship()
    revisions: Mapped[list["WikiRevision"]] = relationship(
        back_populates="page", order_by="desc(WikiRevision.created_at)"
    )


class WikiRevision(Base):
    __tablename__ = "wiki_revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("wiki_pages.id"), index=True)
    edited_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    title: Mapped[str] = mapped_column(Text)
    content_markdown: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    page: Mapped[WikiPage] = relationship(back_populates="revisions")
    edited_by: Mapped[User] = relationship()


class FileItem(Base):
    """Metadata for an uploaded file. The bytes are stored on disk under
    ``settings.uploads_dir / stored_name``; ``stored_name`` is a random
    token, never the original filename, so uploads can't collide or be
    used to escape the uploads directory."""

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)
    household_id: Mapped[int] = mapped_column(ForeignKey("households.id"), index=True)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    stored_name: Mapped[str] = mapped_column(Text, unique=True, default=_uuid)
    original_filename: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(Text, default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(default=0)
    description: Mapped[str] = mapped_column(Text, default="")

    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    uploaded_by: Mapped[User] = relationship()

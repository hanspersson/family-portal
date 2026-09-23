# Family Portal — project context for Claude Code

This file is for picking the project back up in Claude Code. `README.md`
is the user-facing doc (what it is, how to run it); this one is
developer/agent-facing: decisions made, why, and what's left.

## What this is

A self-hosted family portal for a small household (2-6 people): shared
calendar, wiki, and file storage, tied together with one login per
family member. Target deployment is a home server/NAS, reachable over
the home network (or a VPN/Tailscale) rather than the public internet.

## Stack and why

- **Flask** (not FastAPI — this project started on FastAPI and was
  ported to Flask on request). Blueprints per feature area, an app
  factory (`create_app()`), `flask run` for dev / `gunicorn` for prod.
- **SQLAlchemy 2.0** with typed `Mapped[...]` models, **SQLite** as the
  single-file database (easy backup, no DB server to run).
- **Jinja2** server-rendered templates, no JS framework, no build step —
  deliberately simple, works fine on a phone browser.
- **Flask's built-in session** (signed cookie via `SECRET_KEY`) for
  login state; `bcrypt` (used directly, not via passlib -- see
  `security.py`) for password hashing. No external auth service.
- **uv** for dependency management (`pyproject.toml` + `uv.lock` once
  `uv sync` has run somewhere with PyPI access).
- Typed Python throughout (the user asked for type hints consistently
  on an earlier, related project and the same preference carried over
  here).

## Architecture

```
src/family_portal/
  __init__.py         create_app(): builds the Flask app, wires config,
                        DB engine, and all blueprints
  wsgi.py               WSGI entry point (family_portal.wsgi:app) + a
                          `run()` used by the `family-portal` console script
  config.py               Config class, reads FAMILY_PORTAL_* env vars
                            (and a .env file via python-dotenv)
  database.py               Engine/sessionmaker stored on app.extensions
                              (not module globals) so tests can build a
                              fully separate app + SQLite file with no
                              monkeypatching; DB session is request-scoped
                              via Flask's `g`
  models.py                  ORM models — see its module docstring for
                               the full data-model writeup
  security.py                  hash_password / verify_password only
                                 (session signing is Flask's, not custom)
  formatting.py                  Jinja filters (localtime, filesize) +
                                   local_now(); see "Times" below
  deps.py                        get_current_user() + @login_required
                                   decorator (redirects to /login, since
                                   these are HTML pages, not a JSON API)
  blueprints/
    auth.py     first-run setup, login/logout, add family members
    dashboard.py  home page: upcoming events, recent wiki/file activity
    calendar.py    month view, add/delete events
    wiki.py         pages + edit history (every save keeps a WikiRevision)
    files.py         upload/list/download/delete
  templates/    one Jinja2 template per page, extending base.html
  static/style.css  hand-written, no framework/CDN
tests/          pytest + Flask test client: test_smoke.py (one per
                  feature) + test_regressions.py (one per fixed bug)
```

### Data model / sharing model

Every content table (`Event`, `WikiPage`, `FileItem`, ...) has a
`household_id`. **Everyone in a household currently sees everything in
it** — that's the whole sharing model for v1, deliberately simple. The
`household_id` on every table is the seam for adding finer-grained
sharing later (e.g. a `visible_to` join table) without restructuring.

Login is invite-only from inside the app: the first visit to `/login`
with zero users in the DB shows a setup form that creates the household
+ the first (admin) account; after that, an admin (only admins --
enforced server-side) adds further family members from `/members`.
Usernames are normalized in one place (`_normalize_username` in
`auth.py`: trim + lowercase) and must match `[a-z0-9._-]+`. There's no
public sign-up and no password-reset flow (a home server usually has no
outbound mail configured for that).

### Times

SQLite drops timezone offsets. Bookkeeping timestamps (`created_at`,
`updated_at`, `uploaded_at`) are written as UTC and come back naive UTC:
display them through the `localtime` Jinja filter (`formatting.py`).
Calendar event times are naive *local* wall-clock times as typed in and
are displayed as-is; compare them against `local_now()`, never UTC.
Display timezone: `FAMILY_PORTAL_TIMEZONE`, default the server's own.

## Status

Originally written in a sandbox with no PyPI access, so it was never run
there. Since then it has been installed (`uv sync`) on the user's
machine and the test suite run: all 8 smoke tests pass.

First bug found and fixed on that first run: `passlib` 1.7.4
(unmaintained) crashes against `bcrypt` 5 during its backend self-test,
which broke every signup/login. `security.py` now calls `bcrypt`
directly and truncates to bcrypt's 72-byte limit explicitly; existing
`$2b$` hashes stay compatible.

A headless-Chrome click-through (setup, login, calendar, wiki, files,
members, non-admin account) was then done on 2026-09-23. The bugs it
found are fixed, each with a test in `tests/test_regressions.py`: any
member could add members (now admin-only), stored XSS via wiki markdown
(output now sanitized with `nh3`), 500 on duplicate usernames,
unreachable wiki page titled "New", UTC timestamps shown as local time,
"0.0 KB" file sizes, inconsistent username normalization, and delete
redirecting to the wrong month. 20 tests pass.

## Conventions to keep

- **One commit per task step.** The project is a local git repo
  (branch `main`, no remote). Every completed task step gets its own
  commit, with a message that describes that step, rather than
  batching several changes into one commit. Run `uv run pytest` before
  committing code changes.

- Type hints on all function signatures (matches the user's stated
  preference from their other Python project).
- `from __future__ import annotations` at the top of every module.
- Docstrings that explain *why*, not just what, especially for the
  household-scoping/sharing model and the security-relevant bits
  (random file storage names, same-site-only login redirects).
- Keep routes' hardcoded template paths and blueprint route paths in
  sync if you rename anything — templates mostly don't use `url_for`
  for the app's own routes (a carryover from the original FastAPI
  version, which had no `url_for` equivalent wired up); `url_for` is
  used blueprint-to-blueprint in Python code (e.g. redirects after a
  POST).

## Suggested next steps

1. Reverse proxy + HTTPS (Caddy/nginx/Traefik) or a Tailscale/VPN setup
   if it'll be reachable outside the home network — it currently serves
   plain HTTP.
2. iCal export/import for the calendar.
3. Per-item sharing (private notes/files visible to only some family
   members) — the household-scoping groundwork is already there.
4. Regular backups of `data/family_portal.db` + `uploads/` together
   (that's the entire state of the app).

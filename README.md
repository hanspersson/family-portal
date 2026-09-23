# Family Portal

A self-hosted family portal: one shared place for the household calendar,
a wiki (house rules, recipes, emergency info, anything worth writing
down), and shared file storage — meant to run on a home server or NAS
for a small family (2-6 people).

## Stack

- **Python 3.11**, typed (type hints throughout), managed with `uv`.
- **Flask** for the web app and routing (blueprints per feature area).
- **SQLAlchemy 2.0** (typed models) + **SQLite** for storage — a single
  file, easy to back up, no separate database server to run.
- **Jinja2** server-rendered templates (Flask's built-in templating) — no
  JS build step, works well on a phone browser, and stays simple to
  maintain for a project like this.
- Session auth via Flask's built-in signed-cookie session + `bcrypt`
  for password hashing — no external auth service needed.
- **gunicorn** for production serving; Flask's dev server for local use.

## Project layout

```
src/family_portal/
  __init__.py         create_app() factory: config, DB, blueprint wiring
  wsgi.py              WSGI entry point (`family_portal.wsgi:app`)
  config.py             Settings (env-overridable)
  database.py             SQLAlchemy engine/session, scoped per request via Flask's `g`
  models.py                 ORM models (Household, User, Event, WikiPage,
                              WikiRevision, FileItem) — see the module
                              docstring for the data model and sharing model
  security.py                Password hashing
  deps.py                      current-user lookup + `login_required` decorator
  blueprints/
    auth.py                     First-run setup, login/logout, family members
    dashboard.py                  Home page (upcoming events, recent activity)
    calendar.py                     Calendar (month view, add/delete events)
    wiki.py                          Wiki pages + edit history
    files.py                          File upload/list/download/delete
  templates/                   Jinja2 templates (one per page)
  static/style.css              Hand-written CSS, no framework/CDN
tests/                        pytest + Flask test client smoke tests
```

## How it fits together

- **Household = the sharing boundary.** Every table (`Event`,
  `WikiPage`, `FileItem`, ...) has a `household_id`. Everyone in a
  household currently sees everything in it — that's "sharing between
  family members" for v1. The household FK is deliberately there on
  every table so finer-grained sharing (e.g. "just visible to
  me + Mom") can be added later as a join table, without restructuring
  anything.
- **First run** (`/login` with zero users in the DB) shows a setup form
  that creates the household and the first (admin) account. After that,
  the admin can add other family members from **Family** in the nav —
  that's how new logins get created; there's no public sign-up.
- **Wiki** keeps every edit as a `WikiRevision` row, so nothing a family
  member writes gets silently overwritten.
- **Files** are stored on disk under `uploads/`, named by a random token
  (not the original filename) with the real name kept in the database —
  avoids collisions and path-traversal issues from uploaded filenames.

## Running it

```bash
cd family-portal
uv sync                # installs all dependencies into .venv/
cp .env.example .env   # then edit .env and set a real FAMILY_PORTAL_SECRET_KEY
                        # (generate one with: openssl rand -hex 32)

# Quick / development:
uv run flask --app family_portal.wsgi --debug run --host 0.0.0.0 --port 8000
# or: uv run family-portal

# Production (recommended for anything left running):
uv sync --group prod
uv run gunicorn -w 2 -b 0.0.0.0:8000 family_portal.wsgi:app
```

Then open `http://<server-ip>:8000` from any device on your network —
the first visit walks you through creating the family and your account.

Run the test suite with:

```bash
uv run pytest
```

## Suggested next steps

- **Reverse proxy + HTTPS**: put this behind Caddy/nginx/Traefik (or a
  Tailscale/VPN setup) if it'll be reachable outside your home network —
  it currently serves plain HTTP with no TLS of its own.
- **Backups**: back up `data/family_portal.db` and the `uploads/`
  directory together (they're the entire state of the app).
- **iCal export/import** for the calendar, if you want it to show up in
  Apple/Google Calendar too.
- **Per-item sharing** (e.g. private notes/files visible to only some
  family members) — the household-scoping groundwork is already there.
- **Password reset** flow — currently an admin has to set a new password
  for someone directly (there's no email-based reset since a home server
  usually doesn't have outbound mail configured).

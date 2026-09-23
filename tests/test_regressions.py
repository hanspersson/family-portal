"""Regression tests for bugs found during the first browser click-through."""

from __future__ import annotations


def _sign_up(client) -> None:
    client.post(
        "/setup",
        data={
            "household_name": "The Test Family",
            "display_name": "Ada",
            "username": "ada",
            "password": "correct-horse-battery",
        },
    )


def _add_member(client, username: str, *, is_admin: bool = False):
    data = {"display_name": username.title(), "username": username, "password": "member-password"}
    if is_admin:
        data["is_admin"] = "true"
    return client.post("/members", data=data)


def _login(client, username: str, password: str = "member-password"):
    return client.post("/login", data={"username": username, "password": password})


def test_non_admin_cannot_add_members(client):
    _sign_up(client)
    _add_member(client, "kid")
    client.post("/logout")
    _login(client, "kid")

    assert _add_member(client, "intruder").status_code == 403
    page = client.get("/members")
    assert b"@intruder" not in page.data
    assert b"Add a family member" not in page.data


def test_wiki_strips_scripts_but_keeps_formatting(client):
    _sign_up(client)
    client.post(
        "/wiki/new",
        data={
            "title": "Evil",
            "content_markdown": (
                "## Heading\n\n> quoted\n\n"
                '<script>alert(1)</script><img src="x" onerror="alert(2)">'
                "[link](javascript:alert(3))"
            ),
        },
    )
    page = client.get("/wiki/evil").data
    assert b"<script>" not in page
    assert b"onerror" not in page
    assert b"javascript:" not in page
    assert b'<h2 id="heading">' in page
    assert b"<blockquote>" in page


def test_duplicate_username_shows_error_not_500(client):
    _sign_up(client)
    _add_member(client, "kid")
    response = _add_member(client, "kid")
    assert response.status_code == 400
    assert b"already taken" in response.data


def test_wiki_page_titled_new_is_reachable(client):
    _sign_up(client)
    response = client.post("/wiki/new", data={"title": "New", "content_markdown": "fresh"})
    assert response.location.endswith("/wiki/new-2")
    assert b"fresh" in client.get("/wiki/new-2").data


def test_timestamps_shown_in_configured_timezone(client):
    from datetime import datetime, timezone

    from family_portal.formatting import localtime

    client.application.config["TIMEZONE"] = "Europe/Stockholm"
    with client.application.app_context():
        # Stored UTC comes back naive; 17:30 UTC is 19:30 in Stockholm (CEST).
        shown = localtime(datetime(2026, 9, 23, 17, 30))
        assert shown.strftime("%H:%M") == "19:30"
        assert localtime(datetime(2026, 9, 23, 17, 30, tzinfo=timezone.utc)) == shown


def test_dashboard_upcoming_uses_local_wall_clock(client):
    from datetime import timedelta

    from family_portal.formatting import local_now

    # Pick a zone far from UTC so a UTC-vs-local mix-up would be visible.
    client.application.config["TIMEZONE"] = "Pacific/Kiritimati"  # UTC+14
    _sign_up(client)
    with client.application.app_context():
        now = local_now()
    past = now - timedelta(hours=3)
    soon = now + timedelta(hours=2)
    for title, start in (("Already over", past), ("Coming up", soon)):
        client.post(
            "/calendar/new",
            data={"title": title, "start_at": start.strftime("%Y-%m-%dT%H:%M")},
        )
    page = client.get("/").data
    assert b"Coming up" in page
    assert b"Already over" not in page


def test_filesize_formatting():
    from family_portal.formatting import filesize

    assert filesize(1) == "1 byte"
    assert filesize(20) == "20 bytes"
    assert filesize(1536) == "1.5 KB"
    assert filesize(5 * 1024 * 1024) == "5.0 MB"
    assert filesize(3 * 1024**4) == "3072.0 GB"


def test_usernames_normalized_the_same_everywhere(client):
    client.post(
        "/setup",
        data={
            "household_name": "Fam",
            "display_name": "Ada",
            "username": "  Ada.L ",
            "password": "correct-horse-battery",
        },
    )
    _add_member(client, "Bea_K")
    members = client.get("/members").data
    assert b"@ada.l" in members
    assert b"@bea_k" in members

    client.post("/logout")
    response = _login(client, "BEA_K")
    assert response.location in ("/", "http://localhost/")


def test_invalid_username_rejected_with_message(client):
    _sign_up(client)
    response = _add_member(client, "bad name!")
    assert response.status_code == 400
    assert b"may only use" in response.data
    assert b"badname" not in client.get("/members").data


def test_setup_rejects_invalid_username(client):
    response = client.post(
        "/setup",
        data={"household_name": "Fam", "display_name": "Ada", "username": "a d a", "password": "x" * 10},
    )
    assert response.status_code == 400
    assert b"may only use" in response.data


def test_delete_event_returns_to_its_month(client):
    _sign_up(client)
    client.post("/calendar/new", data={"title": "Far away", "start_at": "2031-03-10T09:00"})
    response = client.post("/calendar/1/delete")
    assert response.location.endswith("/calendar?month=2031-03")
    assert b"Far away" not in client.get("/calendar?month=2031-03").data

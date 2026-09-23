"""Smoke tests covering the first-run setup flow and one action in each
of the four features (calendar, wiki, files, sharing via family members),
so a broken import or wiring mistake fails loudly instead of only at
`uv run` time in production.
"""

from __future__ import annotations

import io


def _sign_up(client) -> None:
    response = client.post(
        "/setup",
        data={
            "household_name": "The Test Family",
            "display_name": "Ada",
            "username": "ada",
            "password": "correct-horse-battery",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.location in ("/", "http://localhost/")


def test_first_run_redirects_to_setup(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Let&#39;s set up your family portal" in response.data or b"set up your family portal" in response.data


def test_setup_then_dashboard(client):
    _sign_up(client)
    response = client.get("/")
    assert response.status_code == 200
    assert b"Hi Ada" in response.data


def test_second_login_after_setup(client):
    _sign_up(client)
    client.post("/logout")
    response = client.get("/login")
    assert b"Log in" in response.data
    assert b"set up your family portal" not in response.data


def test_calendar_create_and_list(client):
    _sign_up(client)
    client.post(
        "/calendar/new",
        data={
            "title": "Dentist",
            "start_at": "2030-01-15T09:00",
            "end_at": "2030-01-15T10:00",
        },
        follow_redirects=False,
    )
    response = client.get("/calendar?month=2030-01")
    assert response.status_code == 200
    assert b"Dentist" in response.data


def test_wiki_create_edit_and_history(client):
    _sign_up(client)
    client.post(
        "/wiki/new",
        data={"title": "House Rules", "content_markdown": "# Be kind"},
        follow_redirects=False,
    )
    page = client.get("/wiki/house-rules")
    assert b"Be kind" in page.data

    client.post(
        "/wiki/house-rules/edit",
        data={"title": "House Rules", "content_markdown": "# Be kind\n\nAlways."},
        follow_redirects=False,
    )
    updated = client.get("/wiki/house-rules")
    assert b"Always" in updated.data

    history = client.get("/wiki/house-rules/history")
    assert history.status_code == 200


def test_file_upload_list_download(client):
    _sign_up(client)
    upload_response = client.post(
        "/files/upload",
        data={
            "upload": (io.BytesIO(b"hello family"), "note.txt"),
            "description": "test note",
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert upload_response.status_code == 302

    listing = client.get("/files")
    assert b"note.txt" in listing.data

    download = client.get("/files/1/download")
    assert download.status_code == 200
    assert download.data == b"hello family"


def test_sharing_add_family_member(client):
    _sign_up(client)
    client.post(
        "/members",
        data={"display_name": "Beatrice", "username": "bea", "password": "another-strong-pw"},
        follow_redirects=False,
    )
    members = client.get("/members")
    assert b"Beatrice" in members.data


def test_logged_out_user_is_redirected(client):
    response = client.get("/calendar", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.location

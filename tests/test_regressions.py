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

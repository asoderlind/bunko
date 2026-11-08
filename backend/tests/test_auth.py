"""Password hashing and session token round-trip."""

from app.auth import hash_password, issue_session, verify_password


def test_password_roundtrip():
    h = hash_password("changeme-qa-only")
    assert verify_password(h, "changeme-qa-only")
    assert not verify_password(h, "wrong")


def test_hashes_are_salted():
    assert hash_password("same") != hash_password("same")


def test_issue_session_sets_cookie():
    from fastapi import Response

    r = Response()
    issue_session(r, 1)
    cookie = r.headers["set-cookie"]
    assert "easy_notes_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie

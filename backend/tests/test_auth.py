"""Password hashing and session token round-trip."""

import os

# Test-only credential. Override with EASY_NOTES_TEST_PASSWORD if you prefer;
# it never has to match a real deployment.
TEST_PASSWORD = os.environ.get("EASY_NOTES_TEST_PASSWORD", "test-password-not-a-real-secret")


def _auth():
    """Imported lazily: a bad SECRET_KEY makes the import itself raise."""
    from app import auth

    return auth


def test_password_roundtrip():
    auth = _auth()
    h = auth.hash_password(TEST_PASSWORD)
    assert auth.verify_password(h, TEST_PASSWORD)
    assert not auth.verify_password(h, "wrong")


def test_hashes_are_salted():
    auth = _auth()
    assert auth.hash_password("same") != auth.hash_password("same")


def test_issue_session_sets_cookie():
    from fastapi import Response

    r = Response()
    _auth().issue_session(r, 1)
    cookie = r.headers["set-cookie"]
    assert "bunko_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


def test_blank_secret_key_is_refused(monkeypatch):
    """A blank key would sign forgeable cookies, so startup must fail."""
    import importlib

    from app import config

    monkeypatch.setenv("SECRET_KEY", "")
    config.get_settings.cache_clear()
    try:
        with __import__("pytest").raises(RuntimeError, match="SECRET_KEY is empty"):
            if "app.auth" in __import__("sys").modules:
                importlib.reload(__import__("sys").modules["app.auth"])
            else:
                importlib.import_module("app.auth")
    finally:
        monkeypatch.undo()
        config.get_settings.cache_clear()

"""Password hashing and signed-cookie sessions.

Replaces Django's auth + session middleware with the minimum this single-user
app needs: Argon2id hashes and an itsdangerous-signed cookie.
"""

from __future__ import annotations

from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Cookie, Depends, HTTPException, Response, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_session
from app.models import AppUser

settings = get_settings()

# Argon2id with library defaults (memory-hard, OWASP-recommended).
_hasher = PasswordHasher()

# A blank key still signs cookies, and itsdangerous will happily accept them —
# meaning anyone who can read this source could forge a session. Refuse to
# start rather than run with a forgeable empty key.
if not settings.secret_key.strip():
    raise RuntimeError("SECRET_KEY is empty. Generate one with: openssl rand -base64 48")
if len(settings.secret_key) < 32:
    raise RuntimeError("SECRET_KEY is too short; use at least 32 characters.")

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="session")

COOKIE_NAME = settings.session_cookie
MSG_NOT_AUTHENTICATED = "Authentication credentials were not provided."
STATUS_NOT_AUTHENTICATED = status.HTTP_403_FORBIDDEN


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def issue_session(response: Response, user_id: int) -> None:
    token = _serializer.dumps({"uid": user_id})
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=settings.session_max_age,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def _user_id_from_cookie(token: str | None) -> int | None:
    if not token:
        return None
    try:
        data = _serializer.loads(token, max_age=settings.session_max_age)
    except BadSignature:
        return None
    uid = data.get("uid") if isinstance(data, dict) else None
    return uid if isinstance(uid, int) else None


def current_user(
    session: Annotated[Session, Depends(get_session)],
    easy_notes_session: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> AppUser:
    """Require an authenticated user."""
    uid = _user_id_from_cookie(easy_notes_session)
    if uid is None:
        raise HTTPException(STATUS_NOT_AUTHENTICATED, MSG_NOT_AUTHENTICATED)

    user = session.get(AppUser, uid)
    if user is None or not user.is_active:
        raise HTTPException(STATUS_NOT_AUTHENTICATED, MSG_NOT_AUTHENTICATED)
    return user


def optional_user(
    session: Annotated[Session, Depends(get_session)],
    easy_notes_session: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> AppUser | None:
    uid = _user_id_from_cookie(easy_notes_session)
    if uid is None:
        return None
    user = session.get(AppUser, uid)
    return user if user and user.is_active else None


def find_user_by_password(session: Session, password: str) -> AppUser | None:
    """Single-user app: match the password against any active user."""
    stmt = select(AppUser).where(AppUser.is_active.is_(True)).order_by(AppUser.id)
    for user in session.scalars(stmt):
        if verify_password(user.password_hash, password):
            return user
    return None

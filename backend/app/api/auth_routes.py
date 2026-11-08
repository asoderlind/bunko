"""Auth endpoints: password-only login, logout, and an identity probe."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    clear_session,
    current_user,
    find_user_by_password,
    issue_session,
    optional_user,
)
from app.db import get_session
from app.models import AppUser
from app.schemas import LoginIn, UserOut

router = APIRouter(tags=["auth"])

SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/user", response_model=UserOut | None)
def whoami(user: Annotated[AppUser | None, Depends(optional_user)]) -> UserOut | None:
    """Auth probe for the SPA. Returns null when signed out."""
    if user is None:
        return None
    return UserOut(id=user.id, username=user.username)


@router.post("/auth/login", response_model=UserOut)
def login(payload: LoginIn, response: Response, session: SessionDep) -> UserOut:
    user: AppUser | None = None
    if payload.username:
        user = session.scalars(select(AppUser).where(AppUser.username == payload.username)).first()
        from app.auth import verify_password

        if user is not None and not verify_password(user.password_hash, payload.password):
            user = None
    else:
        user = find_user_by_password(session, payload.password)

    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong password.")

    issue_session(response, user.id)
    return UserOut(id=user.id, username=user.username)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    clear_session(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/auth/me", response_model=UserOut)
def me(user: Annotated[AppUser, Depends(current_user)]) -> UserOut:
    return UserOut(id=user.id, username=user.username)

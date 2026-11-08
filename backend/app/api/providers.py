"""Provider profiles. API key env var NAMES only, never keys."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_session
from app.models import AppUser, ProviderProfile
from app.schemas import Page, ProviderIn, ProviderOut

router = APIRouter(prefix="/providers", tags=["providers"], redirect_slashes=True)
# Accept both /api/providers and /api/providers/ : the SPA uses the trailing form.

SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[AppUser, Depends(current_user)]


@router.get("", response_model=Page[ProviderOut])
def list_providers(session: SessionDep, _user: UserDep) -> Page[ProviderOut]:
    rows = session.scalars(select(ProviderProfile)).all()
    return Page[ProviderOut](
        count=len(rows),
        next=False,
        previous=False,
        results=[ProviderOut.model_validate(p) for p in rows],
    )


@router.post("", response_model=ProviderOut, status_code=status.HTTP_201_CREATED)
def create_provider(payload: ProviderIn, session: SessionDep, _user: UserDep) -> ProviderOut:
    if payload.is_default:
        session.execute(update(ProviderProfile).values(is_default=False))
    profile = ProviderProfile(**payload.model_dump())
    session.add(profile)
    session.commit()
    return ProviderOut.model_validate(profile)


@router.put("/{provider_id}", response_model=ProviderOut)
def update_provider(
    provider_id: uuid.UUID, payload: ProviderIn, session: SessionDep, _user: UserDep
) -> ProviderOut:
    profile = session.get(ProviderProfile, provider_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")

    if payload.is_default:
        session.execute(
            update(ProviderProfile).where(ProviderProfile.id != profile.id).values(is_default=False)
        )
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    session.commit()
    return ProviderOut.model_validate(profile)

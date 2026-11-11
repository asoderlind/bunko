"""Provider profiles. API keys are write-only through the API."""

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
        results=[
            ProviderOut(
                id=p.id,
                label=p.label,
                base_url=p.base_url,
                model=p.model,
                api_key_env=p.api_key_env,
                api_key_set=bool(p.api_key or p.api_key_env),
                is_default=p.is_default,
                is_local=p.is_local,
                enabled=p.enabled,
            )
            for p in rows
        ],
    )


@router.post("", response_model=ProviderOut, status_code=status.HTTP_201_CREATED)
def create_provider(payload: ProviderIn, session: SessionDep, _user: UserDep) -> ProviderOut:
    if payload.is_default:
        session.execute(update(ProviderProfile).values(is_default=False))
    data = payload.model_dump()
    api_key = data.pop("api_key", None)
    profile = ProviderProfile(**data, api_key=api_key or "")
    session.add(profile)
    session.commit()
    return ProviderOut(
        id=profile.id,
        label=profile.label,
        base_url=profile.base_url,
        model=profile.model,
        api_key_env=profile.api_key_env,
        api_key_set=bool(profile.api_key or profile.api_key_env),
        is_default=profile.is_default,
        is_local=profile.is_local,
        enabled=profile.enabled,
    )


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
    data = payload.model_dump(exclude_unset=True)
    if "api_key" in data:
        profile.api_key = data.pop("api_key") or ""
    for key, value in data.items():
        setattr(profile, key, value)
    session.commit()
    return ProviderOut(
        id=profile.id,
        label=profile.label,
        base_url=profile.base_url,
        model=profile.model,
        api_key_env=profile.api_key_env,
        api_key_set=bool(profile.api_key or profile.api_key_env),
        is_default=profile.is_default,
        enabled=profile.enabled,
        is_local=profile.is_local,
    )

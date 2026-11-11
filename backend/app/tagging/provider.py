"""Provider selection rules shared by APIs and the tagging worker."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProviderProfile


def resolve_provider(session: Session, local_only: bool) -> ProviderProfile | None:
    """Select the configured provider, respecting private-note restrictions."""
    if local_only:
        # A remote default must never block a private note from using an
        # otherwise available local provider.
        return session.scalars(
            select(ProviderProfile)
            .where(ProviderProfile.enabled.is_(True), ProviderProfile.is_local.is_(True))
            .order_by(ProviderProfile.is_default.desc(), ProviderProfile.label)
        ).first()

    provider = session.scalars(
        select(ProviderProfile).where(
            ProviderProfile.enabled.is_(True), ProviderProfile.is_default.is_(True)
        )
    ).first()
    if provider is not None:
        return provider
    return session.scalars(
        select(ProviderProfile)
        .where(ProviderProfile.enabled.is_(True))
        .order_by(ProviderProfile.is_local, ProviderProfile.label)
    ).first()

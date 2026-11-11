"""Tags API: list, create, patch, merge."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.config import get_settings
from app.db import get_session
from app.models import AppUser, Note, NoteTag, Tag
from app.schemas import (
    Page,
    TagIn,
    TagMergeIn,
    TagOut,
    TagPatch,
    TagSuggestionIn,
    TagSuggestionsOut,
)
from app.tagging import client
from app.tagging.provider import resolve_provider

router = APIRouter(prefix="/tags", tags=["tags"], redirect_slashes=True)
# Accept both /api/tags and /api/tags/ : the SPA uses the trailing form.

SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[AppUser, Depends(current_user)]


def _out(tag: Tag) -> TagOut:
    return TagOut(
        id=tag.id,
        slug=tag.slug,
        name=tag.name,
        description=tag.description,
        color=tag.color,
        note_count=tag.usage_count,
    )


def pick_color(session: Session) -> str:
    """Least-used palette colour, so new tags stay visually distinct."""
    from app.models import TAG_COLORS

    used = session.scalars(select(Tag.color).where(Tag.color != "")).all()
    counts = dict.fromkeys(TAG_COLORS, 0)
    for c in used:
        if c in counts:
            counts[c] += 1
    return min(TAG_COLORS, key=lambda k: (counts[k], TAG_COLORS.index(k)))


@router.get("", response_model=Page[TagOut])
def list_tags(session: SessionDep, _user: UserDep) -> Page[TagOut]:
    rows = session.scalars(select(Tag).order_by(Tag.usage_count.desc(), Tag.slug)).all()
    return Page[TagOut](
        count=len(rows), next=False, previous=False, results=[_out(t) for t in rows]
    )


@router.post("/suggest", response_model=TagSuggestionsOut)
def suggest_tags(
    payload: TagSuggestionIn, session: SessionDep, _user: UserDep
) -> TagSuggestionsOut:
    """Suggest additions to the global tag vocabulary from a safe note sample."""
    settings = get_settings()
    provider = resolve_provider(session, local_only=False)
    if provider is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No enabled provider configured.")

    total = session.scalar(select(func.count()).select_from(Note)) or 0
    eligible_stmt = select(Note)
    if not provider.is_local:
        eligible_stmt = eligible_stmt.where(Note.local_only.is_(False))
    eligible_count = session.scalar(
        select(func.count()).select_from(eligible_stmt.subquery())
    ) or 0
    sampled = session.scalars(
        eligible_stmt.order_by(func.random()).limit(payload.sample_size)
    ).all()

    if not sampled:
        return TagSuggestionsOut(
            provider_label=provider.label,
            provider_is_local=provider.is_local,
            eligible_count=eligible_count,
            sampled_count=0,
            excluded_private_count=total - eligible_count,
            suggestions=[],
        )

    existing = session.scalars(select(Tag).order_by(Tag.slug).limit(200)).all()
    existing_slugs = {tag.slug for tag in existing}
    existing_text = "\n".join(
        f"- {tag.slug}: {tag.name} — {tag.description or '(no description)'}"
        for tag in existing
    ) or "(none)"
    note_text = "\n\n".join(
        f"NOTE {index}: {note.title or '(untitled)'}\n"
        f"EXCERPT: {client.truncate_body(note.body_md, 350)}"
        for index, note in enumerate(sampled, 1)
    )
    prompt = (
        f"EXISTING TAGS:\n{existing_text}\n\n"
        f"NOTE SAMPLE ({len(sampled)} of {eligible_count} eligible notes):\n{note_text}"
    )
    prompt = client.truncate_body(prompt, settings.tagging_max_input_chars)

    try:
        raw = client.call_tag_suggester(provider, prompt, settings.tagging_request_timeout)
        suggestions = client.parse_tag_suggestions(raw, existing_slugs)
    except (client.ProviderError, client.OutputError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)[:200]) from exc

    return TagSuggestionsOut(
        provider_label=provider.label,
        provider_is_local=provider.is_local,
        eligible_count=eligible_count,
        sampled_count=len(sampled),
        excluded_private_count=total - eligible_count,
        suggestions=suggestions,
    )


@router.post("", response_model=TagOut, status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagIn, session: SessionDep, _user: UserDep) -> TagOut:
    if session.scalars(select(Tag).where(Tag.slug == payload.slug)).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A tag with that slug already exists.")

    tag = Tag(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        color=payload.color or pick_color(session),
    )
    session.add(tag)
    session.commit()
    return _out(tag)


@router.patch("/{tag_id}", response_model=TagOut)
def update_tag(tag_id: uuid.UUID, payload: TagPatch, session: SessionDep, _user: UserDep) -> TagOut:
    tag = session.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")

    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] and data["slug"] != tag.slug:
        clash = session.scalars(select(Tag).where(Tag.slug == data["slug"])).first()
        if clash is not None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "A tag with that slug already exists.")
        tag.slug = data["slug"]
    for field in ("name", "description", "color"):
        if field in data and data[field] is not None:
            setattr(tag, field, data[field])

    session.commit()
    return _out(tag)


@router.post("/{tag_id}/merge", response_model=TagOut)
def merge_tag(
    tag_id: uuid.UUID, payload: TagMergeIn, session: SessionDep, _user: UserDep
) -> TagOut:
    source = session.get(Tag, tag_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    target = session.scalars(select(Tag).where(Tag.slug == payload.merge_into)).first()
    if target is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No tag with that slug.")
    if target.id == source.id:
        return _out(target)

    # Move NoteTag rows, skipping notes that already have the target tag.
    already = set(session.scalars(select(NoteTag.note_id).where(NoteTag.tag_id == target.id)).all())
    moved = session.scalars(select(NoteTag).where(NoteTag.tag_id == source.id)).all()
    for nt in moved:
        if nt.note_id in already:
            session.delete(nt)
        else:
            nt.tag_id = target.id

    session.flush()
    # usage_count is denormalised; recompute rather than increment.
    for tag in (source, target):
        tag.usage_count = (
            session.scalar(
                select(func.count()).select_from(NoteTag).where(NoteTag.tag_id == tag.id)
            )
            or 0
        )

    session.delete(source)
    session.commit()
    return _out(target)

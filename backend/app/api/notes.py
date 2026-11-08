"""Notes API. Preserves the behaviour the SPA and worker rely on."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.auth import current_user
from app.db import get_session
from app.models import AppUser, Note, NoteTag, Tag, TagSource, TagStatus, TitleSource
from app.schemas import (
    NoteIn,
    NoteOut,
    NotePatch,
    NoteTagOut,
    Page,
    TagPinIn,
    TagsResponse,
)

router = APIRouter(prefix="/notes", tags=["notes"], redirect_slashes=True)
# Accept both /api/notes and /api/notes/ : the SPA uses the trailing form.

SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[AppUser, Depends(current_user)]


def _note_tags_out(note: Note) -> list[NoteTagOut]:
    return [
        NoteTagOut(
            id=nt.id,
            tag_id=nt.tag.id,
            slug=nt.tag.slug,
            name=nt.tag.name,
            color=nt.tag.color,
            source=nt.source,
            confidence=nt.confidence,
        )
        for nt in note.note_tags
    ]


def _note_out(note: Note) -> NoteOut:
    return NoteOut(
        id=note.id,
        body_md=note.body_md,
        title=note.title,
        title_source=note.title_source,
        tags=_note_tags_out(note),
        tag_status=note.tag_status,
        tag_error=note.tag_error,
        local_only=note.local_only,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def _load(session: Session, note_id: uuid.UUID) -> Note:
    note = session.scalars(
        select(Note)
        .where(Note.id == note_id)
        .options(selectinload(Note.note_tags).selectinload(NoteTag.tag))
    ).first()
    if note is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    return note


def _recount(session: Session, tag: Tag) -> None:
    tag.usage_count = (
        session.scalar(select(func.count()).select_from(NoteTag).where(NoteTag.tag_id == tag.id))
        or 0
    )


@router.get("", response_model=Page[NoteOut])
def list_notes(
    session: SessionDep,
    _user: UserDep,
    q: str | None = None,
    tag: Annotated[list[str] | None, Query()] = None,
    tag_status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> Page[NoteOut]:
    stmt = select(Note).options(selectinload(Note.note_tags).selectinload(NoteTag.tag))

    if tag:
        # Every requested tag must be present (AND), matching the old API.
        for slug in tag:
            stmt = stmt.where(
                Note.id.in_(select(NoteTag.note_id).join(Tag).where(Tag.slug == slug))
            )

    if tag_status:
        stmt = stmt.where(Note.tag_status == tag_status)

    if q:
        # Simple ILIKE across body and title. Replaces Postgres FTS; for a
        # single-user note collection this is comfortably fast and has no
        # stemming surprises ("trading" no longer matches "trade" oddly).
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Note.body_md.ilike(pattern), Note.title.ilike(pattern)))

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    stmt = stmt.order_by(Note.updated_at.desc()).offset(max(0, offset))
    if limit is not None:
        stmt = stmt.limit(max(1, min(limit, 200)))

    rows = session.scalars(stmt).unique().all()
    return Page[NoteOut](
        count=total,
        next=(offset + len(rows)) < total,
        previous=offset > 0,
        results=[_note_out(n) for n in rows],
    )


@router.post("", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteIn, session: SessionDep, _user: UserDep) -> NoteOut:
    if not payload.body_md.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Note body cannot be empty.")

    note = Note(
        body_md=payload.body_md,
        local_only=payload.local_only,
        tag_status=TagStatus.PENDING,
    )
    if payload.title is not None and payload.title.strip():
        note.title = payload.title.strip()[:200]
        note.title_source = TitleSource.USER
    else:
        note.title = note.derive_title()
        note.title_source = TitleSource.DERIVED

    session.add(note)
    session.commit()
    return _note_out(_load(session, note.id))


@router.get("/{note_id}", response_model=NoteOut)
def get_note(note_id: uuid.UUID, session: SessionDep, _user: UserDep) -> NoteOut:
    return _note_out(_load(session, note_id))


@router.patch("/{note_id}", response_model=NoteOut)
def update_note(
    note_id: uuid.UUID, payload: NotePatch, session: SessionDep, _user: UserDep
) -> NoteOut:
    note = _load(session, note_id)
    data = payload.model_dump(exclude_unset=True)

    body_changed = "body_md" in data and data["body_md"] != note.body_md
    if "body_md" in data and not (data["body_md"] or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Note body cannot be empty.")

    if "local_only" in data:
        note.local_only = bool(data["local_only"])

    if "title" in data:
        new_title = (data["title"] or "").strip()
        if new_title:
            note.title = new_title[:200]
            note.title_source = TitleSource.USER
        else:
            # Cleared on purpose: hand the title back to the generator.
            note.title = note.derive_title()
            note.title_source = TitleSource.DERIVED
    elif body_changed and note.title_source != TitleSource.USER:
        note.title = note.derive_title()
        note.title_source = TitleSource.DERIVED

    if body_changed:
        note.body_md = data["body_md"]
        note.tag_status = TagStatus.PENDING
        note.tag_error = ""
        note.content_revision += 1

    session.commit()
    return _note_out(_load(session, note.id))


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: uuid.UUID, session: SessionDep, _user: UserDep) -> Response:
    note = _load(session, note_id)
    session.delete(note)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{note_id}/tags", response_model=TagsResponse)
def get_note_tags(note_id: uuid.UUID, session: SessionDep, _user: UserDep) -> TagsResponse:
    note = _load(session, note_id)
    return TagsResponse(
        tag_status=note.tag_status,
        tag_error=note.tag_error,
        tags=_note_tags_out(note),
    )


@router.post("/{note_id}/tags", response_model=TagsResponse)
def add_note_tag(
    note_id: uuid.UUID, payload: TagPinIn, session: SessionDep, _user: UserDep
) -> TagsResponse:
    """Pin an existing tag to a note. Tags are never created here."""
    note = _load(session, note_id)
    tag = session.scalars(select(Tag).where(Tag.slug == payload.slug)).first()
    if tag is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No such tag. Tags must exist before they can be pinned.",
        )

    existing = session.scalars(
        select(NoteTag).where(NoteTag.note_id == note.id, NoteTag.tag_id == tag.id)
    ).first()
    if existing is None:
        session.add(NoteTag(note_id=note.id, tag_id=tag.id, source=TagSource.MANUAL))
    elif existing.source != TagSource.MANUAL:
        existing.source = TagSource.MANUAL

    session.flush()
    _recount(session, tag)
    session.commit()
    return TagsResponse(
        tag_status=note.tag_status,
        tag_error=note.tag_error,
        tags=_note_tags_out(_load(session, note.id)),
    )


@router.delete("/{note_id}/tags/{tag_id}", response_model=TagsResponse)
def remove_note_tag(
    note_id: uuid.UUID, tag_id: uuid.UUID, session: SessionDep, _user: UserDep
) -> TagsResponse:
    note = _load(session, note_id)
    nt = session.scalars(
        select(NoteTag).where(NoteTag.note_id == note.id, NoteTag.tag_id == tag_id)
    ).first()
    if nt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    tag = nt.tag
    session.delete(nt)
    session.flush()
    _recount(session, tag)
    session.commit()
    return TagsResponse(
        tag_status=note.tag_status,
        tag_error=note.tag_error,
        tags=_note_tags_out(_load(session, note.id)),
    )


__all__: list[Any] = [router]

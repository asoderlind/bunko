"""Folders API: flat list with optional one-level nesting."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_session
from app.models import AppUser, Folder, Note
from app.schemas import FolderIn, FolderOut, FolderPatch

router = APIRouter(prefix="/folders", tags=["folders"])

SessionDep = Annotated[Session, Depends(get_session)]
UserDep = Annotated[AppUser, Depends(current_user)]


def _counts(session: Session) -> dict[uuid.UUID, int]:
    rows = session.execute(
        select(Note.folder_id, func.count())
        .where(Note.folder_id.is_not(None))
        .group_by(Note.folder_id)
    ).all()
    return {fid: n for fid, n in rows if fid is not None}


def _out(folder: Folder, counts: dict[uuid.UUID, int]) -> FolderOut:
    return FolderOut(
        id=folder.id,
        name=folder.name,
        parent_id=folder.parent_id,
        position=folder.position,
        collapsed=folder.collapsed,
        note_count=counts.get(folder.id, 0),
    )


@router.get("", response_model=list[FolderOut])
def list_folders(session: SessionDep, _user: UserDep) -> list[FolderOut]:
    counts = _counts(session)
    folders = session.scalars(select(Folder).order_by(Folder.position, Folder.name)).all()
    return [_out(f, counts) for f in folders]


@router.post("", response_model=FolderOut, status_code=status.HTTP_201_CREATED)
def create_folder(payload: FolderIn, session: SessionDep, _user: UserDep) -> FolderOut:
    if payload.parent_id is not None and session.get(Folder, payload.parent_id) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parent folder does not exist.")

    # Append at the end of the sibling list.
    last = session.scalar(
        select(func.max(Folder.position)).where(Folder.parent_id == payload.parent_id)
    )
    folder = Folder(
        name=payload.name.strip(),
        parent_id=payload.parent_id,
        position=(last or 0) + 1,
    )
    session.add(folder)
    session.commit()
    return _out(folder, _counts(session))


@router.patch("/{folder_id}", response_model=FolderOut)
def update_folder(
    folder_id: uuid.UUID, payload: FolderPatch, session: SessionDep, _user: UserDep
) -> FolderOut:
    folder = session.get(Folder, folder_id)
    if folder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")

    data = payload.model_dump(exclude_unset=True)
    if "parent_id" in data and data["parent_id"] == folder.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A folder cannot contain itself.")
    for field in ("name", "parent_id", "position", "collapsed"):
        if field in data:
            setattr(folder, field, data[field])

    session.commit()
    return _out(folder, _counts(session))


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(folder_id: uuid.UUID, session: SessionDep, _user: UserDep):
    """Delete a folder. Its notes are unfiled (SET NULL), not deleted."""
    folder = session.get(Folder, folder_id)
    if folder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    session.delete(folder)
    session.commit()
    return None

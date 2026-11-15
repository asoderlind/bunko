"""Portable Markdown front matter and transactional note imports."""

import re
from datetime import UTC, date, datetime

import yaml
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Folder, Note, NoteTag, Tag, TagSource, TagStatus, TitleSource
from app.tagging.provider import resolve_provider


class Metadata(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str | None = Field(default=None, max_length=200)
    date: datetime | None = None
    updated: datetime | None = None
    tags: list[str] | None = None
    folder: list[str] | None = None
    private: StrictBool = False

    @field_validator("date", "updated", mode="before")
    @classmethod
    def parse_date(cls, value):
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(value, datetime.min.time(), tzinfo=UTC)
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not isinstance(value, datetime):
            raise ValueError("Expected an ISO date or timestamp")
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @field_validator("folder", mode="before")
    @classmethod
    def folder_path(cls, value):
        return [value] if isinstance(value, str) else value

    @field_validator("tags", "folder")
    @classmethod
    def validate_names(cls, value):
        if value is not None:
            if any(not name.strip() or len(name) > 100 for name in value):
                raise ValueError("Names must be non-empty and at most 100 characters")
            return [name.strip() for name in value]
        return value


def parse_markdown(content: str) -> tuple[Metadata, str]:
    content = content.removeprefix("\ufeff")
    lines = content.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return Metadata(), content
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ValueError("Front matter is missing its closing --- delimiter")
    header = "".join(lines[1:end])
    if len(header) > 65536:
        raise ValueError("Front matter is too large")
    # No object construction or aliases; imported files are untrusted input.
    if any(isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken))
           for token in yaml.scan(header)):
        raise ValueError("YAML anchors and aliases are not supported")
    data = yaml.safe_load(header)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Front matter must be a mapping")
    if "date" not in data and "created" in data:
        data["date"] = data["created"]
    return Metadata.model_validate(data), "".join(lines[end + 1:])


def export_markdown(note: Note) -> str:
    path = []
    folder = note.folder
    seen = set()
    while folder is not None and folder.id not in seen:
        seen.add(folder.id)
        path.insert(0, folder.name)
        folder = folder.parent
    metadata = {
        "title": note.title,
        "date": note.created_at.isoformat(),
        "updated": note.updated_at.isoformat(),
        "tags": [link.tag.slug for link in note.note_tags],
        "folder": path or None,
        "private": note.local_only,
    }
    header = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
    return "---\n" + header + "---\n" + note.body_md


def import_markdown(
    session: Session, content: str, generate_tags: bool, generate_title: bool,
    *, commit: bool = True,
) -> Note:
    metadata, body = parse_markdown(content)
    if not body.strip():
        raise ValueError("Note body cannot be empty")
    generate_tags = generate_tags and metadata.tags is None and not metadata.private
    generate_title = generate_title and metadata.title is None and not metadata.private
    queued = (generate_tags or generate_title) and resolve_provider(session, False) is not None
    note = Note(
        body_md=body,
        local_only=metadata.private,
        title=metadata.title or "",
        title_source=TitleSource.USER if metadata.title is not None else TitleSource.DERIVED,
        generation_mode=(
            "both" if generate_tags and generate_title else "title" if generate_title else "tags"
        ),
        tag_status=TagStatus.PENDING if queued else TagStatus.DONE,
    )
    if metadata.title is None:
        note.title = note.derive_title()
    if metadata.date is not None:
        note.created_at = metadata.date
    if metadata.updated is not None:
        note.updated_at = metadata.updated
    elif metadata.date is not None:
        note.updated_at = metadata.date
    parent_id = None
    for name in metadata.folder or []:
        folder = session.scalars(select(Folder).where(
            Folder.name == name, Folder.parent_id == parent_id,
        )).first()
        if folder is None:
            folder = Folder(name=name, parent_id=parent_id)
            session.add(folder)
            session.flush()
        parent_id = folder.id
    note.folder_id = parent_id
    session.add(note)
    session.flush()
    linked = set()
    for name in metadata.tags or []:
        tag = session.scalars(select(Tag).where(Tag.slug == name)).first()
        if tag is None:
            tag = session.scalars(select(Tag).where(Tag.name == name)).first()
        if tag is None:
            slug = re.sub(r"[^\w-]+", "-", name.lower()).strip("-") or "tag"
            base = slug[:90]
            slug = base
            suffix = 1
            while session.scalars(select(Tag).where(Tag.slug == slug)).first() is not None:
                suffix += 1
                slug = f"{base}-{suffix}"
            tag = Tag(slug=slug, name=name)
            session.add(tag)
            session.flush()
        if tag.id not in linked:
            linked.add(tag.id)
            session.add(NoteTag(note_id=note.id, tag_id=tag.id, source=TagSource.MANUAL))
            tag.usage_count += 1
    if commit:
        session.commit()
    else:
        session.flush()
    return note

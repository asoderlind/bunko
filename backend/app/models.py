"""SQLAlchemy models. Mirrors the schema Django created."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(UTC)


class TagStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class TitleSource(StrEnum):
    DERIVED = "derived"
    GENERATED = "generated"
    USER = "user"


class TagSource(StrEnum):
    AUTO = "auto"
    MANUAL = "manual"


TAG_COLORS: tuple[str, ...] = (
    "blue",
    "green",
    "amber",
    "red",
    "purple",
    "pink",
    "teal",
    "orange",
    "slate",
    "lime",
)


class Tag(Base):
    __tablename__ = "notes_tag"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(200), default="")
    color: Mapped[str] = mapped_column(String(20), default="")
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )

    note_tags: Mapped[list[NoteTag]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tag {self.slug}>"


class Folder(Base):
    """A user-made container for notes. One level of nesting via parent_id."""

    __tablename__ = "notes_folder"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("notes_folder.id", ondelete="CASCADE"), nullable=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    collapsed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )

    notes: Mapped[list[Note]] = relationship(back_populates="folder")
    children: Mapped[list[Folder]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )
    parent: Mapped[Folder | None] = relationship(back_populates="children", remote_side="Folder.id")

    def __repr__(self) -> str:
        return f"<Folder {self.name}>"


class Note(Base):
    __tablename__ = "notes_note"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    body_md: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(200), default="")
    title_source: Mapped[str] = mapped_column(String(20), default=TitleSource.DERIVED)
    tag_status: Mapped[str] = mapped_column(String(20), default=TagStatus.PENDING, index=True)
    local_only: Mapped[bool] = mapped_column(Boolean, default=False)

    # Bumped on every body write that should invalidate in-flight tagging.
    content_revision: Mapped[int] = mapped_column(Integer, default=0)

    tag_error: Mapped[str] = mapped_column(String(200), default="")

    # Notes survive folder deletion; they fall back to "unfiled".
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("notes_folder.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now
    )

    note_tags: Mapped[list[NoteTag]] = relationship(
        back_populates="note", cascade="all, delete-orphan"
    )
    folder: Mapped[Folder | None] = relationship(back_populates="notes")

    __table_args__ = (Index("notes_note_status_updated_idx", "tag_status", "updated_at"),)

    def derive_title(self) -> str:
        """First non-empty line, stripped of markdown heading marks."""
        for line in self.body_md.splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                return stripped[:200]
        return ""

    def __repr__(self) -> str:
        return f"<Note {self.id}>"


class NoteTag(Base):
    __tablename__ = "notes_notetag"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    note_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("notes_note.id", ondelete="CASCADE")
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("notes_tag.id", ondelete="CASCADE")
    )
    source: Mapped[str] = mapped_column(String(10), default=TagSource.AUTO)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )

    note: Mapped[Note] = relationship(back_populates="note_tags")
    tag: Mapped[Tag] = relationship(back_populates="note_tags")

    __table_args__ = (UniqueConstraint("note_id", "tag_id", name="uniq_note_tag"),)


class ProviderProfile(Base):
    __tablename__ = "notes_providerprofile"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    label: Mapped[str] = mapped_column(String(100))
    base_url: Mapped[str] = mapped_column(String(200))
    model: Mapped[str] = mapped_column(String(100))
    # Legacy compatibility for profiles created with OLLAMA_* variables.
    # New profiles store the provider key in api_key instead.
    api_key_env: Mapped[str] = mapped_column(String(100), default="")
    api_key: Mapped[str] = mapped_column(String(500), default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_local: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        # At most one default, enforced in the database rather than in code.
        Index(
            "uniq_default_provider",
            "is_default",
            unique=True,
            postgresql_where=text("is_default"),
            sqlite_where=text("is_default = 1"),
        ),
    )


class AppUser(Base):
    """The single local user. Replaces Django's auth_user."""

    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )

    __table_args__ = (CheckConstraint("length(username) > 0", name="username_not_empty"),)


class Attachment(Base):
    """Reserved for v1.1. Created but unused."""

    __tablename__ = "notes_attachment"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    note_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("notes_note.id", ondelete="CASCADE")
    )
    file: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(100))
    byte_size: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )

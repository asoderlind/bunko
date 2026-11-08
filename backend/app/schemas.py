"""Pydantic schemas for the API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    description: str
    color: str
    note_count: int = 0


class TagIn(BaseModel):
    slug: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=200)
    color: str = Field(default="", max_length=20)

    @field_validator("slug")
    @classmethod
    def slug_lowercase(cls, v: str) -> str:
        if v != v.lower():
            raise ValueError("slug must be lowercase")
        return v


class TagPatch(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=200)
    color: str | None = Field(default=None, max_length=20)


class TagMergeIn(BaseModel):
    merge_into: str


class TagPinIn(BaseModel):
    slug: str


class NoteTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tag_id: uuid.UUID
    slug: str
    name: str
    color: str
    source: str
    confidence: float | None


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    body_md: str
    title: str
    title_source: str
    tags: list[NoteTagOut] = []
    tag_status: str
    tag_error: str
    local_only: bool
    created_at: datetime
    updated_at: datetime


class NoteIn(BaseModel):
    body_md: str
    title: str | None = None
    local_only: bool = False


class NotePatch(BaseModel):
    body_md: str | None = None
    title: str | None = None
    local_only: bool | None = None


class TagsResponse(BaseModel):
    tag_status: str
    tag_error: str
    tags: list[NoteTagOut]


class ProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    base_url: str
    model: str
    api_key_env: str
    is_default: bool
    is_local: bool
    enabled: bool


class ProviderIn(BaseModel):
    label: str
    base_url: str
    model: str
    api_key_env: str = ""
    is_default: bool = False
    is_local: bool = False
    enabled: bool = True


class LoginIn(BaseModel):
    password: str
    username: str | None = None


class UserOut(BaseModel):
    id: int
    username: str


class Page[T](BaseModel):
    count: int
    next: bool
    previous: bool
    results: list[T]

"""Markdown round trips and metadata precedence."""

from datetime import date

import pytest
from app.markdown_io import export_markdown, import_markdown, parse_markdown
from app.models import Base, Folder, Tag
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


def test_round_trip(session):
    source = '''---
title: 'A title: "quoted"'
date: 2026-03-25
updated: 2026-03-26T14:00:00Z
tags: [painting, blog]
folder: [Personal, Art]
private: true
layout: post
---
# Painting

Some content.
'''
    note = import_markdown(session, source, True, True)
    assert note.local_only is True
    assert note.tag_status == "done"
    assert note.created_at.date() == date(2026, 3, 25)
    assert note.title == 'A title: "quoted"'
    assert note.folder.name == "Art"
    assert note.folder.parent.name == "Personal"
    assert {link.tag.slug for link in note.note_tags} == {"painting", "blog"}
    exported = export_markdown(note)
    restored = import_markdown(session, exported, True, True)
    assert restored.body_md == note.body_md
    assert restored.title == note.title
    assert restored.updated_at == note.updated_at
    assert restored.folder_id == note.folder_id
    assert restored.local_only
    assert len(session.scalars(select(Tag)).all()) == 2
    assert len(session.scalars(select(Folder)).all()) == 2
    assert all(tag.usage_count == 2 for tag in session.scalars(select(Tag)))


@pytest.mark.parametrize(
    ("header", "mode", "status"),
    [
        ("title: Fixed\n", "tags", "pending"),
        ("tags: []\n", "title", "pending"),
        ("title: Fixed\ntags: []\n", "tags", "done"),
        ("private: true\n", "tags", "done"),
    ],
)
def test_metadata_overrides_generation(session, monkeypatch, header, mode, status):
    monkeypatch.setattr("app.markdown_io.resolve_provider", lambda *_: object())
    note = import_markdown(session, f"---\n{header}---\nBody", True, True)
    assert note.generation_mode == mode
    assert note.tag_status == status
    assert not note.note_tags


def test_zip_export_contains_separate_notes(session):
    from io import BytesIO
    from zipfile import ZipFile

    from app.api.notes import export_notes

    first = import_markdown(session, "# Same title\nFirst", False, False)
    second = import_markdown(session, "---\nprivate: true\n---\n# Same title\nSecond", False, False)
    response = export_notes(session, None)
    assert response.media_type == "application/zip"
    with ZipFile(BytesIO(response.body)) as archive:
        assert set(archive.namelist()) == {f"{first.id}.md", f"{second.id}.md"}
        metadata, body = parse_markdown(archive.read(f"{second.id}.md").decode())
        assert metadata.private is True
        assert body == second.body_md


def test_plain_markdown(session):
    note = import_markdown(session, "\n# Beginning\n\nBody", False, False)
    assert note.title == "Beginning"
    assert note.body_md == "\n# Beginning\n\nBody"
    assert note.tag_status == "done"
    assert not note.local_only


@pytest.mark.parametrize("header", [
    'private: "false"',
    "tags: invalid",
    "date: invalid",
    "- not-a-mapping",
    "title: !!python/object:object {}",
    "tags: &tags [a]\nfolder: *tags",
])
def test_invalid_metadata_is_rejected(header):
    import yaml

    with pytest.raises((ValueError, yaml.YAMLError)):
        parse_markdown(f"---\n{header}\n---\nBody")


def test_legacy_dates_and_windows_newlines():
    metadata, body = parse_markdown("\ufeff---\r\ncreated: 2026-03-25\r\n---\r\nBody")
    assert metadata.date.date() == date(2026, 3, 25)
    assert body == "Body"

"""Explicit generation actions must not modify the other kind of metadata."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.mark.parametrize("mode", ["title", "tags", "both"])
def test_generation_updates_only_requested_metadata(mode):
    from app.models import Base, Note, NoteTag, Tag, TagSource, TagStatus, TitleSource
    from app.worker import claim_one, complete

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        note = Note(
            body_md="A note about testing",
            title="Original title",
            title_source=TitleSource.GENERATED,
            tag_status=TagStatus.PENDING,
            generation_mode=mode,
        )
        old_tag = Tag(slug="existing", name="Existing")
        new_tag = Tag(slug="new", name="New")
        session.add_all([note, old_tag, new_tag])
        session.flush()
        session.add(NoteTag(note_id=note.id, tag_id=old_tag.id, source=TagSource.AUTO))
        session.commit()
        claimed = claim_one(session)
        complete(session, claimed, [{"slug": "new", "confidence": 0.9}], "New title")
        session.refresh(note)
        assert note.title == ("Original title" if mode == "tags" else "New title")
        assert {link.tag.slug for link in note.note_tags} == (
            {"existing"} if mode == "title" else {"existing", "new"}
        )
        assert note.tag_status == TagStatus.DONE


def test_title_endpoint_preserves_existing_metadata(monkeypatch):
    from app.api import notes
    from app.models import Base, Note, NoteTag, Tag, TagSource, TagStatus, TitleSource

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(notes, "resolve_provider", lambda *_: object())
    with Session(engine, expire_on_commit=False) as session:
        note = Note(body_md="Test", title="My title", title_source=TitleSource.USER)
        tag = Tag(slug="existing", name="Existing")
        session.add_all([note, tag])
        session.flush()
        session.add(NoteTag(note_id=note.id, tag_id=tag.id, source=TagSource.AUTO))
        session.commit()
        result = notes.generate_title(note.id, session, None)
        assert result.title == "My title"
        assert [t.slug for t in result.tags] == ["existing"]
        assert note.generation_mode == "title"
        assert note.tag_status == TagStatus.PENDING


@pytest.mark.parametrize(
    ("generate_tags", "generate_title", "mode", "status"),
    [
        (True, True, "both", "pending"),
        (True, False, "tags", "pending"),
        (False, True, "title", "pending"),
        (False, False, "tags", "done"),
    ],
)
def test_import_generation_options(monkeypatch, generate_tags, generate_title, mode, status):
    from app.api import notes
    from app.models import Base, Note
    from app.schemas import NoteIn

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(notes, "resolve_provider", lambda *_: object())
    with Session(engine, expire_on_commit=False) as session:
        result = notes.create_note(
            NoteIn(
                body_md="\n# First line\n\nNote content",
                generate_tags=generate_tags,
                generate_title=generate_title,
            ),
            session,
            None,
        )
        assert result.title == "First line"
        assert result.body_md == "\n# First line\n\nNote content"
        assert result.tag_status == status
        assert session.get(Note, result.id).generation_mode == mode


def test_private_notes_never_resolve_a_provider():
    from unittest.mock import Mock

    from app.tagging.provider import resolve_provider

    session = Mock()
    assert resolve_provider(session, True) is None
    session.scalars.assert_not_called()


def test_private_worker_skips_provider(monkeypatch):
    from unittest.mock import Mock

    from app import worker

    complete = Mock()
    resolve = Mock()
    monkeypatch.setattr(worker, "complete", complete)
    monkeypatch.setattr(worker, "_resolve_profile", resolve)
    session = Mock()
    claimed = {"id": "private-note", "local_only": True}
    worker.tag_note(session, claimed)
    resolve.assert_not_called()
    complete.assert_called_once_with(session, claimed, [])


def test_generation_prompts_are_separate():
    from app.tagging.client import build_system_prompt

    assert "Do not generate tags" in build_system_prompt([], mode="title")
    assert "Do not generate a title" in build_system_prompt([], mode="tags")
    assert "Also propose a short title" in build_system_prompt([])

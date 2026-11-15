"""Collection restore is metadata-preserving, bounded, and atomic."""

from datetime import UTC
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from app.collection_io import import_collection
from app.markdown_io import import_markdown
from app.models import Base, Folder, Note, Tag
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


def archive(files):
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as output:
        for name, content in files:
            output.writestr(name, content)
    return buffer.getvalue()


def test_export_import_collection(session, monkeypatch):
    from app.api.notes import export_notes

    source = "---\ntitle: Saved\ntags: [art]\nfolder: [Personal]\nprivate: true\n---\nBody"
    original = import_markdown(session, source, False, False)
    exported = export_notes(session, None).body
    monkeypatch.setattr(
        "app.markdown_io.resolve_provider",
        lambda *_: pytest.fail("Collection imports must not call providers"),
    )
    assert import_collection(session, exported) == 1
    notes = session.scalars(select(Note).order_by(Note.id)).all()
    assert len(notes) == 2
    restored = next(note for note in notes if note.id != original.id)
    assert restored.body_md == original.body_md
    assert restored.title == original.title
    assert restored.local_only
    assert restored.folder_id == original.folder_id
    assert restored.tag_status == "done"
    # SQLite returns naive UTC timestamps after reloading a row.
    assert restored.created_at.replace(tzinfo=UTC) == original.created_at.replace(tzinfo=UTC)
    assert [link.tag.slug for link in restored.note_tags] == ["art"]


def test_failed_collection_rolls_back_notes_tags_and_folders(session):
    existing = import_markdown(session, "Existing", False, False)
    content = archive([
        ("valid.md", "---\ntags: [new]\nfolder: [New]\n---\nValid"),
        ("invalid.md", "---\nprivate: invalid\n---\nInvalid"),
    ])
    with pytest.raises(ValueError, match=r"invalid\.md"):
        import_collection(session, content)
    assert session.scalars(select(Note)).all() == [existing]
    assert session.scalars(select(Tag)).all() == []
    assert session.scalars(select(Folder)).all() == []


@pytest.mark.parametrize("filename", ["../bad.md", "/bad.md", "bad.txt", "dir\\bad.md"])
def test_rejects_invalid_entries(session, filename):
    with pytest.raises(ValueError):
        import_collection(session, archive([(filename, "Body")]))
    assert session.scalars(select(Note)).all() == []


def test_rejects_invalid_zip(session):
    with pytest.raises(ValueError, match="ZIP"):
        import_collection(session, b"not a zip")


def test_expanded_size_limit(session, monkeypatch):
    monkeypatch.setattr("app.collection_io.MAX_EXPANDED_BYTES", 10)
    with pytest.raises(ValueError, match="Expanded"):
        import_collection(session, archive([("large.md", "x" * 100)]))


def test_plain_notes_never_generate_on_collection_import(session, monkeypatch):
    monkeypatch.setattr(
        "app.markdown_io.resolve_provider",
        lambda *_: pytest.fail("No generation during restore"),
    )
    assert import_collection(session, archive([("plain.md", "# Plain\nBody")])) == 1
    note = session.scalars(select(Note)).one()
    assert note.title == "Plain"
    assert note.tag_status == "done"

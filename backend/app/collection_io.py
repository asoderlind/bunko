"""Bounded, atomic collection imports. Never extract archive paths to disk."""

from io import BytesIO
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

import yaml
from sqlalchemy.orm import Session

from app.markdown_io import import_markdown

MAX_ARCHIVE_BYTES = 50 * 1024 * 1024
MAX_EXPANDED_BYTES = 100 * 1024 * 1024
MAX_NOTE_BYTES = 10 * 1024 * 1024
MAX_ENTRIES = 10000


def import_collection(session: Session, content: bytes) -> int:
    if len(content) > MAX_ARCHIVE_BYTES:
        raise ValueError("Collection ZIP must be at most 50 MiB.")
    try:
        with ZipFile(BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ENTRIES:
                raise ValueError("Collection contains too many entries.")
            if sum(entry.file_size for entry in entries) > MAX_EXPANDED_BYTES:
                raise ValueError("Expanded collection must be at most 100 MiB.")
            count = 0
            for entry in entries:
                path = PurePosixPath(entry.filename)
                if path.is_absolute() or ".." in path.parts or "\\" in entry.filename:
                    raise ValueError("Collection contains an unsafe filename.")
                if entry.is_dir():
                    continue
                if path.suffix.lower() != ".md":
                    raise ValueError("Collection must contain only Markdown (.md) files.")
                if entry.flag_bits & 1:
                    raise ValueError("Encrypted collections are not supported.")
                if entry.file_size > MAX_NOTE_BYTES:
                    raise ValueError(f"{entry.filename}: note exceeds 10 MiB.")
                with archive.open(entry) as source:
                    data = source.read(MAX_NOTE_BYTES + 1)
                if len(data) > MAX_NOTE_BYTES:
                    raise ValueError(f"{entry.filename}: note exceeds 10 MiB.")
                try:
                    import_markdown(
                        session, data.decode("utf-8-sig"), False, False, commit=False,
                    )
                except (ValueError, yaml.YAMLError) as exc:
                    raise ValueError(f"{entry.filename}: {exc}") from exc
                count += 1
            session.commit()
            return count
    except (BadZipFile, NotImplementedError, RuntimeError) as exc:
        session.rollback()
        raise ValueError("Invalid or unsupported collection ZIP.") from exc
    except Exception:
        session.rollback()
        raise

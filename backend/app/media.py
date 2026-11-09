"""Persistent media storage for note images.

Images are content-addressed by SHA-256, so identical pastes dedupe. Files
live on a mounted volume and are served through authenticated, same-origin
URLs that are stable enough to embed in Markdown. The API deliberately hides
the storage backend, so this can later be swapped for S3/MinIO without
changing note content.
"""

from __future__ import annotations

import hashlib
import io
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.config import get_settings

settings = get_settings()

# Pillow format name -> (extension, MIME type).
ALLOWED_FORMATS: dict[str, tuple[str, str]] = {
    "PNG": (".png", "image/png"),
    "JPEG": (".jpg", "image/jpeg"),
    "GIF": (".gif", "image/gif"),
    "WEBP": (".webp", "image/webp"),
}

EXTENSION_TYPES: dict[str, str] = {
    extension: content_type for extension, content_type in ALLOWED_FORMATS.values()
}


class InvalidImage(ValueError):
    """The uploaded bytes are not a supported image."""


@dataclass(frozen=True)
class StoredImage:
    key: str
    url: str
    content_type: str
    size_bytes: int
    width: int
    height: int


def _inspect_image(data: bytes) -> tuple[str, str, int, int]:
    """Return (extension, MIME, width, height) or raise InvalidImage."""
    if not data:
        raise InvalidImage("Empty upload.")
    if len(data) > settings.media_max_bytes:
        raise InvalidImage("Image is too large.")

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            fmt = (image.format or "").upper()
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImage("Unsupported image file.") from exc

    if fmt not in ALLOWED_FORMATS:
        raise InvalidImage("Only PNG, JPEG, GIF and WebP images are supported.")
    extension, content_type = ALLOWED_FORMATS[fmt]
    return extension, content_type, width, height


def _root() -> Path:
    return settings.media_dir.resolve()


def media_path(key: str) -> Path:
    """Resolve a validated content key inside the media root."""
    root = _root()
    path = (root / key).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Invalid media key.")
    return path


def store_image(data: bytes) -> StoredImage:
    """Validate, dedupe by hash, and persist an image."""
    extension, content_type, width, height = _inspect_image(data)
    digest = hashlib.sha256(data).hexdigest()
    key = f"{digest[:2]}/{digest[2:]}{extension}"
    path = media_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        # Atomic write: readers never see a partially written image.
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".upload-")
        try:
            with os.fdopen(fd, "wb") as tmp:
                tmp.write(data)
            os.replace(tmp_name, path)
        finally:
            Path(tmp_name).unlink(missing_ok=True)

    return StoredImage(
        key=key,
        url=f"/api/media/{key}",
        content_type=content_type,
        size_bytes=len(data),
        width=width,
        height=height,
    )


def content_type_for(key: str) -> str:
    return EXTENSION_TYPES.get(Path(key).suffix.lower(), "application/octet-stream")

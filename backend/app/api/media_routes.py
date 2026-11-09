"""Authenticated image upload and media streaming endpoints."""

from __future__ import annotations

import logging
import re
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from app.auth import current_user
from app.config import get_settings
from app.media import InvalidImage, content_type_for, media_path, store_image
from app.models import AppUser
from app.schemas import MediaOut

log = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/media", tags=["media"])
UserDep = Annotated[AppUser, Depends(current_user)]

# Content-addressed keys produced by app.media.store_image.
KEY_RE = re.compile(r"^[0-9a-f]{2}/[0-9a-f]{62}\.(png|jpg|gif|webp)$")


@router.post("", response_model=MediaOut)
async def upload_media(
    file: Annotated[UploadFile, File()],
    _user: UserDep,
) -> MediaOut:
    if file.size is not None and file.size > settings.media_max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "Image is too large.",
        )

    data = await file.read(settings.media_max_bytes + 1)
    if len(data) > settings.media_max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "Image is too large.",
        )
    try:
        stored = await run_in_threadpool(store_image, data)
    except InvalidImage as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except Exception as exc:
        log.exception("could not store media")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Media storage is unavailable.",
        ) from exc

    return MediaOut(
        url=stored.url,
        markdown=f"![image]({stored.url})",
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        width=stored.width,
        height=stored.height,
    )


@router.get("/{key:path}")
def get_media(key: str, _user: UserDep) -> FileResponse:
    if not KEY_RE.fullmatch(key):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")

    try:
        path = media_path(key)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.") from exc

    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")

    return FileResponse(
        path,
        media_type=content_type_for(key),
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )

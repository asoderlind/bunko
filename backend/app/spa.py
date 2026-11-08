"""Serve the built SvelteKit app.

Mirrors Open WebUI's SPAStaticFiles: serve real files when they exist, fall
back to index.html only for client-side routes, and never return HTML for a
missing script or stylesheet — a stale tab asking for a deleted chunk should
get a clean 404, not HTML the browser then fails to parse.
"""

from __future__ import annotations

import mimetypes
import posixpath
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from app.config import get_settings

settings = get_settings()

ASSET_SUFFIXES = (
    ".js",
    ".mjs",
    ".css",
    ".map",
    ".json",
    ".webmanifest",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".woff",
    ".woff2",
    ".ttf",
    ".txt",
    ".wasm",
)

IMMUTABLE_PREFIX = "_app/immutable/"


def _resolve(route: str) -> Path | None:
    """Map a URL path to a file inside spa_dir, refusing traversal."""
    clean = posixpath.normpath("/" + route).lstrip("/")
    if clean in ("", "."):
        return None
    root = settings.spa_dir.resolve()
    candidate = (root / clean).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _index() -> HTMLResponse:
    index = settings.spa_dir / "index.html"
    if not index.exists():
        raise HTTPException(404, "SPA not built")
    response = HTMLResponse(index.read_bytes())
    # Always revalidate the shell: a cached index.html keeps pointing at chunk
    # filenames a later build deleted.
    response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


def _file(path: Path, route: str) -> FileResponse:
    content_type, _ = mimetypes.guess_type(str(path))
    response = FileResponse(path, media_type=content_type or "application/octet-stream")
    rel = route.lstrip("/")
    if rel.startswith(IMMUTABLE_PREFIX):
        # Content-hashed filename: cache forever.
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path.suffix == ".html":
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    else:
        response.headers["Cache-Control"] = "public, max-age=3600"
    return response


async def spa(request: Request, route: str = "") -> Response:
    """Static file if it exists, else the SPA shell."""
    if request.method not in ("GET", "HEAD"):
        raise HTTPException(404)

    resolved = _resolve(route)
    if resolved is not None:
        return _file(resolved, route)

    if route.lower().endswith(ASSET_SUFFIXES):
        raise HTTPException(404, f"No such asset: {route}")

    return _index()

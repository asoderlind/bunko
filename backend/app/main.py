"""FastAPI application entrypoint."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import auth_routes, folders, notes, providers, tags
from app.config import get_settings
from app.db import SessionLocal
from app.security_headers import SecurityHeadersMiddleware
from app.spa import spa

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("app")

settings = get_settings()

app = FastAPI(
    title="easy-notes",
    debug=settings.debug,
    docs_url="/api/docs" if settings.debug else None,
    openapi_url="/api/openapi.json" if settings.debug else None,
    redoc_url=None,
)

# Order: compression outermost, then security headers, so headers are stamped
# on the compressed response that actually goes over the wire.
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(SecurityHeadersMiddleware)


@app.middleware("http")
async def normalise_api_slash(request: Request, call_next):
    """Treat /api/notes/ and /api/notes as the same path.

    The SPA was built against Django's APPEND_SLASH and requests the
    trailing-slash form; FastAPI registers the bare path. Rewrite before
    routing so both work and neither falls through to the SPA catch-all.
    """
    path = request.scope.get("path", "")
    if path.startswith("/api/") and len(path) > 5 and path.endswith("/"):
        request.scope["path"] = path.rstrip("/")
    return await call_next(request)


@app.middleware("http")
async def process_time(request: Request, call_next):
    import time

    start = time.monotonic()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.monotonic() - start) * 1000:.1f}ms"
    return response


@app.get("/health", include_in_schema=False)
def health() -> JSONResponse:
    """Liveness: touches no external service."""
    return JSONResponse({"status": True})


@app.get("/ready", include_in_schema=False)
def ready() -> JSONResponse:
    """Readiness: the database is the dependency that matters."""
    try:
        session = SessionLocal()
        try:
            session.execute(text("SELECT 1"))
        finally:
            session.close()
    except Exception as exc:  # any failure means not ready
        return JSONResponse({"status": False, "database": str(exc)[:200]}, status_code=503)
    return JSONResponse({"status": True, "database": True})


for _router in (
    auth_routes.router,
    notes.router,
    tags.router,
    providers.router,
    folders.router,
):
    app.include_router(_router, prefix="/api")

# The SPA catch-all goes last, and explicitly refuses to answer for API or
# health paths: without this guard a trailing-slash mismatch silently returns
# index.html with a 200 instead of a JSON 404.
RESERVED_PREFIXES = ("api/", "health", "ready")


@app.api_route("/{route:path}", methods=["GET", "HEAD"], include_in_schema=False)
async def spa_route(request: Request, route: str):
    if route == "api" or route.startswith(RESERVED_PREFIXES):
        return JSONResponse({"detail": "Not found."}, status_code=404)
    return await spa(request, route)

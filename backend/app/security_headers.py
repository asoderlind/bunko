"""Security headers, in the spirit of Open WebUI's set_security_headers().

Safe defaults are always on; HSTS / CSP / Permissions-Policy are opt-in via env
so a plain-HTTP tailnet setup is not broken by them.
"""

from __future__ import annotations

import os
import re

BASE_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "SAMEORIGIN",
    "Cross-Origin-Opener-Policy": "same-origin",
}

HSTS_PATTERN = re.compile(r"^max-age=(\d+)(;includeSubDomains)?(;preload)?$", re.I)


def build_headers() -> dict[str, str]:
    headers = dict(BASE_HEADERS)

    hsts = os.environ.get("HSTS", "").strip()
    if hsts:
        headers["Strict-Transport-Security"] = (
            hsts if HSTS_PATTERN.match(hsts) else "max-age=31536000;includeSubDomains"
        )

    csp = os.environ.get("CONTENT_SECURITY_POLICY", "").strip()
    if csp:
        headers["Content-Security-Policy"] = csp

    permissions = os.environ.get("PERMISSIONS_POLICY", "").strip()
    if permissions:
        headers["Permissions-Policy"] = permissions

    return headers


class SecurityHeadersMiddleware:
    """Stamp security headers on every response, without overwriting views."""

    def __init__(self, app):
        self.app = app
        # Derived from env only, fixed for the process lifetime.
        self.headers = build_headers()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                existing = {k.lower() for k, _ in message["headers"]}
                for key, value in self.headers.items():
                    if key.lower() not in existing:
                        message["headers"].append((key.encode(), value.encode()))
            await send(message)

        await self.app(scope, receive, send_with_headers)

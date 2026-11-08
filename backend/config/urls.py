from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

from config.views import spa_index

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("notes.urls")),
    path("api-auth/", include("rest_framework.urls")),
]

# Serve built SPA assets (served from /app/spa in the image). Fine for
# dev/QA; a real reverse proxy handles this at M5.
if settings.SPA_DIR.exists():
    urlpatterns += [
        # `serve` reads the URL kwarg named `path`, so capture it as such.
        path("assets/<path:path>", serve, {"document_root": settings.SPA_DIR / "assets"}),
        path("manifest.webmanifest", serve, {"document_root": settings.SPA_DIR, "path": "manifest.webmanifest"}),
        # Client-side routes (/notes/:id, /tags, /inbox) fall back to the shell.
        path("<path:route>", spa_index),
        path("", spa_index),
    ]

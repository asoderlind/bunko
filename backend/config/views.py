from django.conf import settings
from django.http import Http404, HttpResponse


def spa_index(request, route=""):
    """Serve the SPA shell for any non-API route.

    Real asset paths are handled earlier in urls.py; anything else is a
    client-side route and must return index.html so a hard reload works.
    """
    index = settings.SPA_DIR / "index.html"
    if not index.exists():
        raise Http404("SPA not built")
    return HttpResponse(index.read_text(encoding="utf-8"), content_type="text/html")

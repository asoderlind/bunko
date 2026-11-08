"""Django settings for easy-notes."""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be set")

DEBUG = os.environ.get("DJANGO_DEBUG", "0") in ("1", "true", "True", "yes")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

# Phone access goes over the tailnet. When served behind TLS on a real domain
# (M5), set CSRF_TRUSTED_ORIGINS explicitly.
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "notes",
    "tagging",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL", "postgres://easy_notes@postgres:5432/easy_notes"),
        conn_max_age=60,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Built SPA (copied to /app/spa in the image).
import os as _os

# In the image the SPA is at /spa (outside /app so the dev bind mount does not
# shadow it). SPA_DIR env lets us override.
SPA_DIR = Path(_os.environ.get("SPA_DIR", "/spa"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# --- easy-notes specific ---------------------------------------------------

# Tagging worker poll interval when the queue is empty (spec 6).
TAGGING_POLL_SECONDS = float(os.environ.get("TAGGING_POLL_SECONDS", "2"))

# How long a row may sit in `processing` before the reaper requeues it (spec 6).
TAGGING_STALE_SECONDS = int(os.environ.get("TAGGING_STALE_SECONDS", "600"))

# Provider HTTP timeout (spec 6).
TAGGING_REQUEST_TIMEOUT = int(os.environ.get("TAGGING_REQUEST_TIMEOUT", "120"))

# Note body is truncated to this many characters before being sent to the model.
TAGGING_MAX_INPUT_CHARS = int(os.environ.get("TAGGING_MAX_INPUT_CHARS", "6000"))

# Only the N most-used tags are included in the prompt (spec 6).
TAGGING_PROMPT_TAG_LIMIT = int(os.environ.get("TAGGING_PROMPT_TAG_LIMIT", "50"))

# Seeded into ProviderProfile on migrate from OLLAMA_BASE_URL. The tailnet IP can
# change, so it lives in env rather than being hardcoded anywhere.
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "std": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "std"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "tagging": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

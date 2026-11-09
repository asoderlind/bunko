# --- frontend build -------------------------------------------------------
FROM node:22-slim AS frontend
WORKDIR /fe

# pnpm via corepack, pinned by the "packageManager" field in package.json.
RUN corepack enable

# pnpm blocks lifecycle scripts by default; esbuild needs its postinstall to
# fetch the platform binary, so approve it non-interactively before install.
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml frontend/svelte.config.js frontend/vite.config.ts frontend/tsconfig.json ./

RUN pnpm install --frozen-lockfile \
    && pnpm approve-builds esbuild \
    && pnpm rebuild esbuild

COPY frontend/ ./
RUN pnpm exec svelte-kit sync
RUN pnpm run build

# --- python runtime -------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MEDIA_DIR=/data/media

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv pip install --system --no-cache -r pyproject.toml

COPY backend/ /app/
WORKDIR /app

# Built SPA. Kept outside /app so the dev bind-mount of ./backend:/app
# doesn't shadow it.
COPY --from=frontend /fe/build /spa

# Persistent note images. Compose usually bind-mounts this path.
VOLUME ["/data/media"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# Self-initialise the database, then serve the API + built SPA.
CMD ["sh", "-c", "python -m app.cli init-db && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]

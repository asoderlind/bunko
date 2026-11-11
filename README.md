# bunko

Single-user, self-hosted note-taking app. Type on a scratchpad, save, and the
note is automatically tagged and titled a few seconds later by a local LLM.

## Motivation

I wanted a self-hosted note-taking app that I am able to pick up, throw ideas at, and let a simple local LLM do the boring work of categorizing, tagging, and fetching notes.

## Images

**Editing a note**

<img width="1118" height="631" alt="image" src="https://github.com/user-attachments/assets/297255d4-09fe-4289-a24a-cbc8fbdfbe60" />

**Viewing the tags**

<img width="1111" height="630" alt="image" src="https://github.com/user-attachments/assets/4b445473-5954-43e4-82e1-d8973d7bea40" />

## Stack

| Layer | Choice |
| --- | --- |
| Backend | FastAPI + SQLAlchemy 2.0 + Alembic |
| DB | SQLite |
| Frontend | SvelteKit (Svelte 5 runes) + Tailwind + bits-ui. Vite HMR in dev; static SPA in production |
| Editor | CodeMirror 6 with Markdown syntax highlighting |
| Preview | markdown-it + highlight.js + DOMPurify |
| LLM access | OpenAI-compatible HTTP (`/v1/chat/completions`) |
| Orchestration | Docker Compose: `web`, `frontend`; tagging runs in the web process |

In production the SPA is built statically and served by FastAPI. In dev the
`frontend` service runs Vite with HMR; FastAPI is still the API server.

## Repo layout

```
backend/
  app/
    api/            # notes, tags, providers, auth routes
    tagging/        # provider client + prompt
    main.py         # FastAPI app, SPA mount, health
    models.py       # SQLAlchemy models
    worker.py       # tagging queue and background loop
  alembic/          # migrations
  tests/
frontend/           # SvelteKit app
data/               # SQLite database and uploaded note images (gitignored, persistent)
docker-compose.dev.yml
Dockerfile
```

## Running

```bash
cp .env.example .env      # then fill in SECRET_KEY and provider settings
docker compose -f docker-compose.dev.yml up -d --build
```

First run needs a user:

```bash
docker compose -f docker-compose.dev.yml exec web \
  python -m app.cli set-password --username axel
```

The app is bound to the tailnet address in `BIND_HOST` and is not exposed on
the LAN or the internet.

- `http://<BIND_HOST>:8000` — FastAPI-served production build
- `http://<BIND_HOST>:5173` — Vite dev server with hot reload (use this while
  working on the frontend)

## Common commands

```bash
# logs
docker compose -f docker-compose.dev.yml logs -f web frontend

# change the password (prompts twice, nothing echoed)
docker compose -f docker-compose.dev.yml exec web \
  python -m app.cli set-password --username axel

# list tags
docker compose -f docker-compose.dev.yml exec web python -m app.cli tags

# drain the tagging queue once, then exit (normally the web process handles it)
docker compose -f docker-compose.dev.yml exec web python -m app.worker --once

# inspect the SQLite database
docker compose -f docker-compose.dev.yml exec web \
  python -c 'import sqlite3; print(sqlite3.connect("/data/bunko.sqlite3").execute("select name from sqlite_master where type=\\"table\\"").fetchall())'
```

If `docker` needs `sudo`, use `sg docker -c "..."` until you log in again.

## Development

The `frontend` service runs Vite against the bind-mounted `frontend/` tree, so
Svelte, TypeScript, CSS and template edits hot-reload without rebuilding the
Docker image. It proxies `/api`, `/admin` and `/static` to `web:8000` on the
compose network.

```bash
# hot-reloading frontend only
docker compose -f docker-compose.dev.yml up -d frontend

# lint and format
uv run ruff check backend/
uv run ruff format backend/

# type check
uv run ty check backend/

# tests
uv run pytest backend/tests
```

## Media

Images pasted or dropped into the editor are content-addressed and stored under
`data/media/`, which is bind-mounted into the web container at `/data/media`. They are
served through authenticated `/api/media/<sha256>.<ext>` URLs, so the storage
path is private and the Markdown stays portable within the app. Back up the
entire `data/` directory, including both SQLite and media files.

## CI and image publishing

- `.github/workflows/ci.yml` runs backend tests, frontend type checks/build, and a Docker build.
- `.github/workflows/publish.yml` builds and pushes `ghcr.io/<owner>/bunko` on every push to
  `main`, on `v*` tags, and manually via `workflow_dispatch`.

Tags include `main`, `latest`, `sha-<short>`, and semver tags for releases. Images are
built for `linux/amd64`.

To pull the image from the homelab:

```bash
docker pull ghcr.io/<owner>/bunko:latest
```

The published package is private by default. For credential-free pulls, open the
package in GitHub Packages and set its visibility to **Public**. Otherwise use
`docker login ghcr.io` with a token that has `read:packages`.

Pushing uses the automatic `GITHUB_TOKEN` (`packages: write`), so no PAT is needed
in Actions. If the repository still denies the push, set **Settings → Actions →
General → Workflow permissions** to "Read and write permissions".

The image's default command initializes new databases, applies pending Alembic
migrations, starts the web server, and runs one background tagging thread.
Persist `/data` and pass `SECRET_KEY` and `DATABASE_URL` at runtime. Configure
OpenRouter or another OpenAI-compatible provider from **Settings** after signing
in. Keep the deployment to one Uvicorn worker; multiple web processes would
start duplicate tagging loops.

## Provider settings

Open **Settings** from the account menu at the bottom of the sidebar. Add an
OpenRouter provider with:

```text
Base URL: https://openrouter.ai/api/v1
Model:    openai/gpt-4o-mini   # or another OpenRouter model
API key:  your OpenRouter key
```

The API key is stored in the local SQLite database and is never returned by the
API. The old `OLLAMA_*` environment variables and `app.cli seed` command remain
only as deprecated compatibility support.

## Health

- `GET /health` — liveness only, touches no external service
- `GET /ready` — also checks the database

## Conventions

- Never send a `local_only` note to a non-local provider. Enforced in the
  worker, before any network call.
- Provider API keys are write-only through the API and are never returned to the frontend.
- Never let the model create a tag. A tag exists because a human made it.
- The `tag_status` column is the queue. No broker, no Celery.
- UUID primary keys, UTC timestamps, `snake_case` fields.

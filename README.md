# easy-notes

Single-user, self-hosted note-taking app. Type on a scratchpad, save, and the
note is automatically tagged and titled a few seconds later by a local LLM.

Tagging is asynchronous and must never block a save.

## Stack

| Layer | Choice |
| --- | --- |
| Backend | FastAPI + SQLAlchemy 2.0 + Alembic |
| DB | Postgres 16 |
| Frontend | SvelteKit (Svelte 5 runes) + Tailwind + bits-ui, built as a SPA |
| LLM access | OpenAI-compatible HTTP (`/v1/chat/completions`) |
| Orchestration | Docker Compose: `web`, `worker`, `postgres` |

The SPA is built statically and served by FastAPI — there is no Node server.

## Repo layout

```
backend/
  app/
    api/            # notes, tags, providers, auth routes
    tagging/        # provider client + prompt
    main.py         # FastAPI app, SPA mount, health
    models.py       # SQLAlchemy models
    worker.py       # tagging worker
  alembic/          # migrations
  tests/
frontend/           # SvelteKit app
docker-compose.dev.yml
Dockerfile
```

## Running

```bash
cp .env.example .env      # then fill in SECRET_KEY, POSTGRES_PASSWORD
docker compose -f docker-compose.dev.yml up -d --build
```

First run needs a user:

```bash
docker compose -f docker-compose.dev.yml exec web \
  python -m app.cli set-password --username axel
```

The app is bound to the tailnet address in `BIND_HOST` and is not exposed on
the LAN or the internet.

## Common commands

```bash
# logs
docker compose -f docker-compose.dev.yml logs -f web worker

# change the password (prompts twice, nothing echoed)
docker compose -f docker-compose.dev.yml exec web \
  python -m app.cli set-password --username axel

# seed the provider profile from OLLAMA_BASE_URL (first run only)
docker compose -f docker-compose.dev.yml exec web python -m app.cli seed

# list tags
docker compose -f docker-compose.dev.yml exec web python -m app.cli tags

# drain the tagging queue once, then exit
docker compose -f docker-compose.dev.yml exec worker python -m app.worker --once

# psql
docker compose -f docker-compose.dev.yml exec postgres \
  psql -U easy_notes -d easy_notes
```

If `docker` needs `sudo`, use `sg docker -c "..."` until you log in again.

## Development

```bash
# lint and format
uv run ruff check backend/
uv run ruff format backend/

# type check
uv run ty check backend/

# tests
uv run pytest backend/tests
```

## Health

- `GET /health` — liveness only, touches no external service
- `GET /ready` — also checks the database

## Conventions

- Never send a `local_only` note to a non-local provider. Enforced in the
  worker, before any network call.
- Never store API keys in the database — env var *names* only.
- Never let the model create a tag. A tag exists because a human made it.
- The `tag_status` column is the queue. No broker, no Celery.
- UUID primary keys, UTC timestamps, `snake_case` fields.

"""Baseline: the schema as it exists after the Django -> FastAPI port.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-08

The tables were created by Django and are compatible with the SQLAlchemy
models, so this migration is intentionally a no-op: it records that the
baseline has been reached. Existing databases are brought under Alembic with
`alembic stamp 0001_baseline`; fresh databases run `create_all` first, then
stamp, via `app.cli init-db`.
"""

from collections.abc import Sequence

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

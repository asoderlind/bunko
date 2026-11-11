"""Store provider API keys in provider profiles.

Revision ID: 0003_provider_api_key
Revises: 0002_folders
Create Date: 2026-11-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_provider_api_key"
down_revision: str | None = "0002_folders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("notes_providerprofile")}
    if "api_key" not in columns:
        op.add_column(
            "notes_providerprofile",
            sa.Column("api_key", sa.String(length=500), nullable=False, server_default=""),
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("notes_providerprofile")}
    if "api_key" in columns:
        op.drop_column("notes_providerprofile", "api_key")

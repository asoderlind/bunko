"""Separate explicit title and tag generation jobs."""

import sqlalchemy as sa
from alembic import op

revision = "0004_generation_mode"
down_revision = "0003_provider_api_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notes_note",
        sa.Column("generation_mode", sa.String(20), nullable=False, server_default="both"),
    )


def downgrade() -> None:
    op.drop_column("notes_note", "generation_mode")

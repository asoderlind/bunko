"""Add folders and note.folder_id

Revision ID: 0002_folders
Revises: 0001_baseline
Create Date: 2026-11-08

Idempotent: safe whether the tables were created by `init-db` (create_all) or
by this migration on a fresh database.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PgUUID

revision: str = "0002_folders"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("notes_folder"):
        op.create_table(
            "notes_folder",
            sa.Column("id", PgUUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column(
                "parent_id",
                PgUUID(as_uuid=True),
                sa.ForeignKey("notes_folder.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("collapsed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    cols = {c["name"] for c in insp.get_columns("notes_note")}
    if "folder_id" not in cols:
        op.add_column("notes_note", sa.Column("folder_id", PgUUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "notes_note_folder_id_fkey",
            "notes_note",
            "notes_folder",
            ["folder_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("ix_notes_note_folder_id", "notes_note", ["folder_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("notes_note"):
        cols = {c["name"] for c in insp.get_columns("notes_note")}
        if "folder_id" in cols:
            op.drop_index("ix_notes_note_folder_id", table_name="notes_note")
            op.drop_constraint("notes_note_folder_id_fkey", "notes_note", type_="foreignkey")
            op.drop_column("notes_note", "folder_id")
    if insp.has_table("notes_folder"):
        op.drop_table("notes_folder")

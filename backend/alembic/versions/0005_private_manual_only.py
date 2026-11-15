"""Cancel legacy private-note generation and clear its stale failures."""

import sqlalchemy as sa
from alembic import op

revision = "0005_private_manual_only"
down_revision = "0004_generation_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        UPDATE notes_note
        SET tag_status = 'done', tag_error = '', content_revision = content_revision + 1
        WHERE local_only = 1
    """))


def downgrade() -> None:
    # Cancelled jobs and old errors should not be restored.
    pass

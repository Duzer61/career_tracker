"""backfill application status history for existing applications

Revision ID: 47448bcc7f4c
Revises: bb1aed4fa5c4
Create Date: 2026-05-18 11:50:12.440924

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "47448bcc7f4c"
down_revision: Union[str, Sequence[str], None] = "bb1aed4fa5c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill status history for existing applications."""
    op.execute("""
        INSERT INTO application_status_history (application_id, status, changed_at)
        SELECT
            a.id,
            a.status,
            a.created_at
        FROM applications a
        WHERE NOT EXISTS (
            SELECT 1 FROM application_status_history h
            WHERE h.application_id = a.id
        )
    """)


def downgrade() -> None:
    """Remove all backfilled history entries."""
    op.execute("DELETE FROM application_status_history")

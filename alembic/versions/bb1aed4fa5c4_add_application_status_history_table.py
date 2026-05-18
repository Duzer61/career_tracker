"""add application status history table

Revision ID: bb1aed4fa5c4
Revises: e9772b113f4e
Create Date: 2026-05-18 11:47:44.542042

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bb1aed4fa5c4"
down_revision: Union[str, Sequence[str], None] = "e9772b113f4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS application_status_history (
            id SERIAL PRIMARY KEY,
            application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            status applicationstatus NOT NULL,
            changed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("application_status_history")

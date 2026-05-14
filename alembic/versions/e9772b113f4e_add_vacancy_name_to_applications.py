"""add vacancy_name to applications

Revision ID: e9772b113f4e
Revises: edfd18665db3
Create Date: 2026-05-14 12:07:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e9772b113f4e"
down_revision: Union[str, Sequence[str], None] = "edfd18665db3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Add column as nullable
    op.add_column("applications", sa.Column("vacancy_name", sa.String(255), nullable=True))
    # Step 2: Set default value for existing rows
    op.execute("UPDATE applications SET vacancy_name = 'Not specified' WHERE vacancy_name IS NULL")
    # Step 3: Make column NOT NULL
    op.alter_column("applications", "vacancy_name", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("applications", "vacancy_name")

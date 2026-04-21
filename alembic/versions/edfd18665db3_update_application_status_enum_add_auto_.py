"""Update application_status enum: add auto_reject and ignored, rename archived to ignored

Revision ID: edfd18665db3
Revises: 0afb1834114c
Create Date: 2026-04-06 16:06:01.458334

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "edfd18665db3"
down_revision: Union[str, Sequence[str], None] = "0afb1834114c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create a new enum type with the complete set of values (uppercase to match existing)
    op.execute("""
        CREATE TYPE applicationstatus_new AS ENUM (
            'CREATED',
            'HR_INTERVIEW',
            'TECH_INTERVIEW',
            'OFFER',
            'AUTO_REJECT',
            'REJECTED',
            'IGNORED'
        )
    """)

    # Update the column to use the new type, converting 'ARCHIVED' to 'IGNORED'
    op.execute("""
        ALTER TABLE applications
        ALTER COLUMN status TYPE applicationstatus_new
        USING CASE
            WHEN status = 'ARCHIVED' THEN 'IGNORED'::applicationstatus_new
            ELSE status::text::applicationstatus_new
        END
    """)

    # Drop the old enum type
    op.execute("DROP TYPE applicationstatus")

    # Rename the new type to the original name
    op.execute("ALTER TYPE applicationstatus_new RENAME TO applicationstatus")


def downgrade() -> None:
    """Downgrade schema."""
    # Create the old enum type (with 'ARCHIVED' instead of 'IGNORED' and without 'AUTO_REJECT')
    op.execute("""
        CREATE TYPE applicationstatus_old AS ENUM (
            'CREATED',
            'HR_INTERVIEW',
            'TECH_INTERVIEW',
            'OFFER',
            'REJECTED',
            'ARCHIVED'
        )
    """)

    # Update the column back to the old type, converting 'IGNORED' to 'ARCHIVED'
    # Note: 'AUTO_REJECT' values will be converted to 'REJECTED'
    op.execute("""
        ALTER TABLE applications
        ALTER COLUMN status TYPE applicationstatus_old
        USING CASE
            WHEN status = 'IGNORED' THEN 'ARCHIVED'::applicationstatus_old
            WHEN status = 'AUTO_REJECT' THEN 'REJECTED'::applicationstatus_old
            ELSE status::text::applicationstatus_old
        END
    """)

    # Drop the new enum type
    op.execute("DROP TYPE applicationstatus")

    # Rename the old type back to original name
    op.execute("ALTER TYPE applicationstatus_old RENAME TO applicationstatus")

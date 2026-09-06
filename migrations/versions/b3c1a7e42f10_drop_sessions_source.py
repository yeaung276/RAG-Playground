"""drop sessions source

Revision ID: b3c1a7e42f10
Revises: 0caafc246c4f
Create Date: 2026-09-05 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b3c1a7e42f10'
down_revision: Union[str, None] = '0caafc246c4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('sessions', 'source')


def downgrade() -> None:
    # The original column was NOT NULL with no default; backfill 'web' for the
    # existing rows before restoring the constraint.
    op.add_column(
        'sessions',
        sa.Column('source', sa.String(), nullable=False, server_default='web'),
    )
    op.alter_column('sessions', 'source', server_default=None)

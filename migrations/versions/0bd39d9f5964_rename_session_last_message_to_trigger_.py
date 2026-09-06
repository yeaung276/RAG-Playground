"""rename session last_message to trigger_message

Revision ID: 0bd39d9f5964
Revises: 35d200f1a2ac
Create Date: 2026-07-21 17:43:24.276999

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0bd39d9f5964'
down_revision: Union[str, None] = '35d200f1a2ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('sessions', 'last_message', new_column_name='trigger_message')


def downgrade() -> None:
    op.alter_column('sessions', 'trigger_message', new_column_name='last_message')

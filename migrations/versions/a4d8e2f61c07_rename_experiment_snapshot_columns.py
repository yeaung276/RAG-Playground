"""rename experiment snapshot columns

Revision ID: a4d8e2f61c07
Revises: f2c9a4b71e83
Create Date: 2026-10-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a4d8e2f61c07'
down_revision: Union[str, None] = 'f2c9a4b71e83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('experiments', 'snapshot_indexing_config', new_column_name='snapshot_kb_config')
    op.alter_column('experiments', 'snapshot_retreival_config', new_column_name='snapshot_retrieval_config')


def downgrade() -> None:
    op.alter_column('experiments', 'snapshot_retrieval_config', new_column_name='snapshot_retreival_config')
    op.alter_column('experiments', 'snapshot_kb_config', new_column_name='snapshot_indexing_config')

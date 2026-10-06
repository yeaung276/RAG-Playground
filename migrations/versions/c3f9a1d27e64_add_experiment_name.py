"""add experiment name

Revision ID: c3f9a1d27e64
Revises: b8e3f17a5c42
Create Date: 2026-10-06 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f9a1d27e64'
down_revision: Union[str, None] = 'b8e3f17a5c42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('experiments', sa.Column('name', sa.String(), nullable=True))
    op.execute(
        """
        UPDATE experiments e
        SET name = d.name || ' #' || n.run
        FROM datasets d,
             (SELECT id, row_number() OVER (PARTITION BY dataset_id ORDER BY created_at) AS run
              FROM experiments) n
        WHERE d.id = e.dataset_id AND n.id = e.id
        """
    )
    op.alter_column('experiments', 'name', nullable=False)


def downgrade() -> None:
    op.drop_column('experiments', 'name')

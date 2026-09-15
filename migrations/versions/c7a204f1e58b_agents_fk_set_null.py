"""agents model and knowledge fks set null on delete

Revision ID: c7a204f1e58b
Revises: b3d9c05a71e4
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c7a204f1e58b'
down_revision: Union[str, None] = 'b3d9c05a71e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FKS = (
    ('agents_knowledge_id_fkey', 'knowledge_id', 'knowledge_bases'),
    ('agents_model_id_fkey', 'model_id', 'models'),
)


def upgrade() -> None:
    for name, column, target in FKS:
        op.drop_constraint(name, 'agents', type_='foreignkey')
        op.create_foreign_key(
            name, 'agents', target, [column], ['id'], ondelete='SET NULL'
        )


def downgrade() -> None:
    for name, column, target in FKS:
        op.drop_constraint(name, 'agents', type_='foreignkey')
        op.create_foreign_key(name, 'agents', target, [column], ['id'])

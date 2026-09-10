"""add agents table

Revision ID: d5a71c93e820
Revises: c4e1b8a37d92
Create Date: 2026-09-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd5a71c93e820'
down_revision: Union[str, None] = 'c4e1b8a37d92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('agents',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('instruction', sa.String(), nullable=False),
    sa.Column('model_id', sa.String(), nullable=True),
    sa.Column('temperature', sa.Integer(), nullable=False),
    sa.Column('knowledge_id', sa.String(), nullable=True),
    sa.Column('max_step', sa.Integer(), nullable=False),
    sa.Column('tools', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
    sa.Column('handoff', postgresql.JSONB(astext_type=sa.Text()), server_default='{"mode": "none", "targets": []}', nullable=False),
    sa.Column('is_entrypoint', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('tools_dek', sa.LargeBinary(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['knowledge_id'], ['knowledge_bases.id'], ),
    sa.ForeignKeyConstraint(['model_id'], ['models.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', name='uq_agents_name')
    )
    op.create_index(op.f('ix_agents_name'), 'agents', ['name'], unique=False)
    op.create_index(
        'uq_agents_entrypoint', 'agents', ['is_entrypoint'], unique=True,
        postgresql_where=sa.text('is_entrypoint'),
    )
    op.create_index(op.f('ix_agents_model_id'), 'agents', ['model_id'], unique=False)
    op.create_index(op.f('ix_agents_knowledge_id'), 'agents', ['knowledge_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_agents_knowledge_id'), table_name='agents')
    op.drop_index(op.f('ix_agents_model_id'), table_name='agents')
    op.drop_index('uq_agents_entrypoint', table_name='agents')
    op.drop_index(op.f('ix_agents_name'), table_name='agents')
    op.drop_table('agents')

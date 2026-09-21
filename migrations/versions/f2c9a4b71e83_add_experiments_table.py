"""add experiments table

Revision ID: f2c9a4b71e83
Revises: e1b74a2c9f30
Create Date: 2026-09-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f2c9a4b71e83'
down_revision: Union[str, None] = 'e1b74a2c9f30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('experiments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('dataset_id', sa.String(), nullable=False),
        sa.Column('knowledge_id', sa.String(), nullable=True),
        sa.Column('snapshot_retreival_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('snapshot_indexing_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('result_path', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['knowledge_id'], ['knowledge_bases.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_experiments_dataset_id'), 'experiments', ['dataset_id'], unique=False)
    op.create_index(op.f('ix_experiments_knowledge_id'), 'experiments', ['knowledge_id'], unique=False)
    op.create_index(op.f('ix_experiments_status'), 'experiments', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_experiments_status'), table_name='experiments')
    op.drop_index(op.f('ix_experiments_knowledge_id'), table_name='experiments')
    op.drop_index(op.f('ix_experiments_dataset_id'), table_name='experiments')
    op.drop_table('experiments')

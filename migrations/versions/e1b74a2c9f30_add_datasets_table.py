"""add datasets table

Revision ID: e1b74a2c9f30
Revises: c7a204f1e58b
Create Date: 2026-09-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e1b74a2c9f30'
down_revision: Union[str, None] = 'c7a204f1e58b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('datasets',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('source_key', sa.String(), nullable=True),
    sa.Column('result_key', sa.String(), nullable=True),
    sa.Column('model_id', sa.String(), nullable=True),
    sa.Column('sample_per_file', sa.Integer(), nullable=False),
    sa.Column('mix', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('labels', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('error', sa.String(), nullable=True),
    sa.Column('file_count', sa.Integer(), nullable=False),
    sa.Column('parsed_count', sa.Integer(), nullable=False),
    sa.Column('pair_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', name='uq_datasets_name')
    )
    op.create_index(op.f('ix_datasets_name'), 'datasets', ['name'], unique=False)
    op.create_index(op.f('ix_datasets_model_id'), 'datasets', ['model_id'], unique=False)
    op.create_index(op.f('ix_datasets_status'), 'datasets', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_datasets_status'), table_name='datasets')
    op.drop_index(op.f('ix_datasets_model_id'), table_name='datasets')
    op.drop_index(op.f('ix_datasets_name'), table_name='datasets')
    op.drop_table('datasets')

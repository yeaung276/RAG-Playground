"""add models table

Revision ID: c4e1b8a37d92
Revises: b3c1a7e42f10
Create Date: 2026-09-10 10:02:11.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e1b8a37d92'
down_revision: Union[str, None] = 'b3c1a7e42f10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('models',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('provider', sa.String(), nullable=False),
    sa.Column('schema', sa.String(), nullable=False),
    sa.Column('base_url', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('capability', sa.String(), nullable=False),
    sa.Column('api_key_ct', sa.LargeBinary(), nullable=True),
    sa.Column('api_key_dek', sa.LargeBinary(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('provider', 'name', 'capability', name='uq_models_provider_name_capability')
    )
    op.create_index(op.f('ix_models_provider'), 'models', ['provider'], unique=False)
    op.create_index(op.f('ix_models_capability'), 'models', ['capability'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_models_capability'), table_name='models')
    op.drop_index(op.f('ix_models_provider'), table_name='models')
    op.drop_table('models')

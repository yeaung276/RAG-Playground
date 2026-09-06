"""drop knowledge embeddings table

Revision ID: 0caafc246c4f
Revises: a93aa38c3cca
Create Date: 2026-08-01 19:45:33.675568

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0caafc246c4f'
down_revision: Union[str, None] = 'a93aa38c3cca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Stands in for pgvector.sqlalchemy.Vector, which this revision stops depending on
class Vector(sa.types.UserDefinedType):
    def get_col_spec(self, **kw) -> str:
        return 'vector'


def upgrade() -> None:
    op.drop_table('knowledge_embeddings')
    # pgvector commented out, not deleted, to keep history; never created now
    # op.execute('DROP EXTENSION IF EXISTS vector')


def downgrade() -> None:
    # op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.create_table('knowledge_embeddings',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('chunk_id', sa.String(), nullable=False),
    sa.Column('node_id', sa.String(), nullable=False),
    sa.Column('kb_id', sa.String(), nullable=False),
    sa.Column('content', sa.String(), nullable=False),
    sa.Column('source', sa.String(), nullable=False),
    sa.Column('pages', sa.JSON(), nullable=False),
    # sa.Column('embedding', Vector(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['chunk_id'], ['knowledge_chunks.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['kb_id'], ['knowledge_bases.id'], ),
    sa.ForeignKeyConstraint(['node_id'], ['knowledge_nodes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_embeddings_chunk_id'), 'knowledge_embeddings', ['chunk_id'], unique=False)
    op.create_index(op.f('ix_knowledge_embeddings_kb_id'), 'knowledge_embeddings', ['kb_id'], unique=False)
    op.create_index(op.f('ix_knowledge_embeddings_node_id'), 'knowledge_embeddings', ['node_id'], unique=False)
    # pgvector commented out, not deleted, to keep history; never created now
    # op.execute(
    #     'CREATE INDEX ix_knowledge_embeddings_embedding_hnsw '
    #     'ON knowledge_embeddings USING hnsw '
    #     '((embedding::vector(1024)) vector_cosine_ops)'
    # )
    op.execute(
        "CREATE INDEX ix_knowledge_embeddings_content_fts "
        "ON knowledge_embeddings USING gin (to_tsvector('english', content))"
    )

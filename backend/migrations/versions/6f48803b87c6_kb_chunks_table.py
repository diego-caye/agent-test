"""kb_chunks table

Revision ID: 6f48803b87c6
Revises: c7bfd84cbca4
Create Date: 2026-09-15 15:48:36.643149

"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

revision: str = "6f48803b87c6"
down_revision: str | Sequence[str] | None = "c7bfd84cbca4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # La extensión va aquí y no a mano: un clon limpio debe poder migrar de cero.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "kb_chunks",
        sa.Column("chunk_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("categoria", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=64), nullable=False),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=768), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("chunk_id"),
    )
    op.create_index(op.f("ix_kb_chunks_categoria"), "kb_chunks", ["categoria"], unique=False)
    op.create_index(
        "ix_kb_chunks_embedding_hnsw",
        "kb_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        op.f("ix_kb_chunks_embedding_model"), "kb_chunks", ["embedding_model"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_kb_chunks_embedding_model"), table_name="kb_chunks")
    op.drop_index(
        "ix_kb_chunks_embedding_hnsw",
        table_name="kb_chunks",
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.drop_index(op.f("ix_kb_chunks_categoria"), table_name="kb_chunks")
    op.drop_table("kb_chunks")

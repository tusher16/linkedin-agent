"""init: enable pgvector + create users, posts, context_chunks

Revision ID: 0001
Revises:
Create Date: 2026-04-29
"""

from __future__ import annotations

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID as PgUUID

from alembic import op

revision = "0001"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(64), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "posts",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True),
        sa.Column("topic", sa.String(500), nullable=False),
        sa.Column("tone", sa.String(50), nullable=False, server_default="professional"),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("outline", sa.JSON(), nullable=True),
        sa.Column("draft_text", sa.Text(), nullable=True),
        sa.Column("review_score", sa.Integer(), nullable=True),
        sa.Column("iteration", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("external_post_id", sa.String(128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_posts_status", "posts", ["status"])

    op.create_table(
        "context_chunks",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True),
        sa.Column("source_file", sa.String(500), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_context_chunks_source_file", "context_chunks", ["source_file"])


def downgrade() -> None:
    op.drop_index("ix_context_chunks_source_file", table_name="context_chunks")
    op.drop_table("context_chunks")
    op.drop_index("ix_posts_status", table_name="posts")
    op.drop_table("posts")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")

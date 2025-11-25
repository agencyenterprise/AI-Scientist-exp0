"""
Add pgvector and unified search_chunks table for RAG search.

Revision ID: 0006
Revises: 0005
Create Date: 2025-09-16
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Create unified search_chunks table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS search_chunks (
            id SERIAL PRIMARY KEY,
            source_type TEXT NOT NULL CHECK (source_type IN ('imported_chat', 'draft_chat', 'project_draft')),
            conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
            chat_message_id INTEGER REFERENCES chat_messages(id) ON DELETE CASCADE,
            project_draft_id INTEGER REFERENCES project_drafts(id) ON DELETE CASCADE,
            project_draft_version_id INTEGER REFERENCES project_draft_versions(id) ON DELETE CASCADE,
            message_index INTEGER,
            sequence_number INTEGER,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    # Helpful indexes
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_search_chunks_conversation_id
        ON search_chunks(conversation_id);
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_search_chunks_chat_message_id
        ON search_chunks(chat_message_id);
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_search_chunks_project_draft_id
        ON search_chunks(project_draft_id);
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_search_chunks_project_draft_version_id
        ON search_chunks(project_draft_version_id);
        """
    )

    # Vector similarity index (cosine distance)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_search_chunks_embedding
        ON search_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_search_chunks_embedding;")
    op.execute("DROP INDEX IF EXISTS idx_search_chunks_project_draft_version_id;")
    op.execute("DROP INDEX IF EXISTS idx_search_chunks_project_draft_id;")
    op.execute("DROP INDEX IF EXISTS idx_search_chunks_chat_message_id;")
    op.execute("DROP INDEX IF EXISTS idx_search_chunks_conversation_id;")
    op.execute("DROP TABLE IF EXISTS search_chunks;")

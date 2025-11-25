"""
Partition search_chunks by source_type and enforce NOT NULL conversation_id.

Revision ID: 0011
Revises: 0010
Create Date: 2025-09-24
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill conversation_id wherever NULL using project_drafts mapping
    op.execute(
        """
        UPDATE search_chunks sc
        SET conversation_id = pd.conversation_id
        FROM project_drafts pd
        WHERE sc.conversation_id IS NULL AND sc.project_draft_id = pd.id;
        """
    )

    # Create new partitioned table with NOT NULL conversation_id
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS search_chunks_new (
            id BIGSERIAL NOT NULL,
            source_type TEXT NOT NULL CHECK (source_type IN ('imported_chat', 'draft_chat', 'project_draft')),
            conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            chat_message_id INTEGER REFERENCES chat_messages(id) ON DELETE CASCADE,
            project_draft_id INTEGER REFERENCES project_drafts(id) ON DELETE CASCADE,
            project_draft_version_id INTEGER REFERENCES project_draft_versions(id) ON DELETE CASCADE,
            message_index INTEGER,
            sequence_number INTEGER,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (source_type, id)
        ) PARTITION BY LIST (source_type);
        """
    )

    # Partitions per source_type
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS search_chunks_imported_chat PARTITION OF search_chunks_new
        FOR VALUES IN ('imported_chat');

        CREATE TABLE IF NOT EXISTS search_chunks_draft_chat PARTITION OF search_chunks_new
        FOR VALUES IN ('draft_chat');

        CREATE TABLE IF NOT EXISTS search_chunks_project_draft PARTITION OF search_chunks_new
        FOR VALUES IN ('project_draft');
        """
    )

    # Move data into partitioned table
    op.execute(
        """
        INSERT INTO search_chunks_new (
            id, source_type, conversation_id, chat_message_id, project_draft_id,
            project_draft_version_id, message_index, sequence_number, chunk_index,
            text, embedding, created_at, updated_at
        )
        SELECT
            id, source_type, conversation_id, chat_message_id, project_draft_id,
            project_draft_version_id, message_index, sequence_number, chunk_index,
            text, embedding, created_at, updated_at
        FROM search_chunks;
        """
    )

    # Ensure the sequence for id is set above current max(id)
    op.execute(
        """
        SELECT setval(
            pg_get_serial_sequence('search_chunks_new', 'id'),
            COALESCE((SELECT MAX(id) FROM search_chunks_new), 0) + 1,
            false
        );
        """
    )

    # Indexes on partitions
    op.execute(
        """
        -- Conversation index (helps grouping/filtering)
        CREATE INDEX IF NOT EXISTS idx_sc_imported_conv_id ON search_chunks_imported_chat (conversation_id);
        CREATE INDEX IF NOT EXISTS idx_sc_draft_conv_id ON search_chunks_draft_chat (conversation_id);
        CREATE INDEX IF NOT EXISTS idx_sc_pdraft_conv_id ON search_chunks_project_draft (conversation_id);

        -- Supporting indexes (align roughly with previous ones)
        CREATE INDEX IF NOT EXISTS idx_sc_imported_msg_id ON search_chunks_imported_chat (chat_message_id);
        CREATE INDEX IF NOT EXISTS idx_sc_draft_msg_id ON search_chunks_draft_chat (chat_message_id);
        CREATE INDEX IF NOT EXISTS idx_sc_pdraft_id ON search_chunks_project_draft (project_draft_id);
        CREATE INDEX IF NOT EXISTS idx_sc_pdraft_ver_id ON search_chunks_project_draft (project_draft_version_id);

        -- Vector indexes per partition
        CREATE INDEX IF NOT EXISTS idx_sc_imported_embedding ON search_chunks_imported_chat USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        CREATE INDEX IF NOT EXISTS idx_sc_draft_embedding ON search_chunks_draft_chat USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        CREATE INDEX IF NOT EXISTS idx_sc_pdraft_embedding ON search_chunks_project_draft USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """
    )

    # Swap tables
    op.execute(
        """
        ALTER TABLE search_chunks RENAME TO search_chunks_old;
        ALTER TABLE search_chunks_new RENAME TO search_chunks;
        """
    )

    # Drop old table (and its indexes)
    op.execute("DROP TABLE IF EXISTS search_chunks_old;")


def downgrade() -> None:
    # Recreate a non-partitioned table (shape of the original, but keeps NOT NULL conversation_id for safety)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS search_chunks_plain (
            id SERIAL PRIMARY KEY,
            source_type TEXT NOT NULL CHECK (source_type IN ('imported_chat', 'draft_chat', 'project_draft')),
            conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
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

        INSERT INTO search_chunks_plain (
            id, source_type, conversation_id, chat_message_id, project_draft_id,
            project_draft_version_id, message_index, sequence_number, chunk_index,
            text, embedding, created_at, updated_at
        )
        SELECT
            id, source_type, conversation_id, chat_message_id, project_draft_id,
            project_draft_version_id, message_index, sequence_number, chunk_index,
            text, embedding, created_at, updated_at
        FROM search_chunks;

        -- Basic indexes
        CREATE INDEX IF NOT EXISTS idx_search_chunks_conversation_id ON search_chunks_plain(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_search_chunks_chat_message_id ON search_chunks_plain(chat_message_id);
        CREATE INDEX IF NOT EXISTS idx_search_chunks_project_draft_id ON search_chunks_plain(project_draft_id);
        CREATE INDEX IF NOT EXISTS idx_search_chunks_project_draft_version_id ON search_chunks_plain(project_draft_version_id);
        CREATE INDEX IF NOT EXISTS idx_search_chunks_embedding ON search_chunks_plain USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

        ALTER TABLE search_chunks RENAME TO search_chunks_part;
        ALTER TABLE search_chunks_plain RENAME TO search_chunks;
        DROP TABLE IF EXISTS search_chunks_part;
        """
    )

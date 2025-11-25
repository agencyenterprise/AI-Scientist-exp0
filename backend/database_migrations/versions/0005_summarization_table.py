"""
Drop chat digest columns from project drafts.
Create a new table for summarization.

Revision ID: 0005
Revises: 0004
Create Date: 2025-09-12
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE project_drafts DROP COLUMN IF EXISTS chat_digest")
    op.execute("ALTER TABLE project_drafts DROP COLUMN IF EXISTS chat_digest_updated_at")
    op.execute("ALTER TABLE conversations RENAME COLUMN content TO imported_chat;")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS summary;")
    op.execute("ALTER TABLE chat_messages DROP COLUMN IF EXISTS search_vector;")
    op.execute("ALTER TABLE project_draft_versions DROP COLUMN IF EXISTS search_vector;")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS search_vector;")

    # drop triggers
    op.execute("DROP TRIGGER IF EXISTS conversations_search_update ON conversations;")
    op.execute("DROP TRIGGER IF EXISTS chat_messages_search_update ON chat_messages;")
    op.execute(
        "DROP TRIGGER IF EXISTS project_draft_versions_search_update ON project_draft_versions;"
    )

    # drop function
    op.execute("DROP FUNCTION IF EXISTS update_conversation_search_vector;")
    op.execute("DROP FUNCTION IF EXISTS update_chat_message_search_vector;")
    op.execute("DROP FUNCTION IF EXISTS update_project_draft_version_search_vector;")

    # create new tables
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS imported_conversation_summaries (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL,
            external_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_summaries (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL,
            external_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            latest_message_id INTEGER NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE project_drafts ADD COLUMN IF NOT EXISTS chat_digest TEXT")
    op.execute(
        "ALTER TABLE project_drafts ADD COLUMN IF NOT EXISTS chat_digest_updated_at TIMESTAMPTZ"
    )
    op.execute("ALTER TABLE conversations RENAME COLUMN imported_chat TO content;")
    op.execute("DROP TABLE IF EXISTS imported_conversation_summaries")
    op.execute("DROP TABLE IF EXISTS chat_summaries")
    op.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS summary TEXT")

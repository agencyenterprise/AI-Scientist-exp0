"""
Drop legacy conversation_summary table and backfill summaries to conversations.summary.

Revision ID: 0003
Revises: 0002
Create Date: 2025-09-12
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the legacy table
    op.execute("DROP TABLE IF EXISTS conversation_summary")
    op.execute("ALTER TABLE conversations ALTER COLUMN summary SET NOT NULL")


def downgrade() -> None:
    # Make summary column nullable again
    op.execute("ALTER TABLE conversations ALTER COLUMN summary DROP NOT NULL")
    # Recreate table (without restoring data)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_summary (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
        """
    )

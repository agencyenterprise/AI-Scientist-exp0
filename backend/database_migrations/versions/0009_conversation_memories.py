"""
Create table to store conversation memories blocks.

Revision ID: 0009
Revises: 0008
Create Date: 2025-09-19
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_memories (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL,
            memory_source TEXT NOT NULL,
            memories JSONB NOT NULL,
            UNIQUE (conversation_id, memory_source),
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS conversation_memories")

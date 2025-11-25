"""Remove unique constraint on conversations.url and add non-unique index

Revision ID: 0010
Revises: 0009
Create Date: 2025-09-22

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the implicit unique constraint created by "url TEXT UNIQUE NOT NULL"
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name = 'conversations'
                  AND constraint_type = 'UNIQUE'
                  AND constraint_name = 'conversations_url_key'
            ) THEN
                ALTER TABLE conversations DROP CONSTRAINT conversations_url_key;
            END IF;
        END $$;
    """
    )

    # Create a non-unique index for fast lookups by URL
    op.execute("CREATE INDEX IF NOT EXISTS idx_conversations_url ON conversations(url)")


def downgrade() -> None:
    # Remove the non-unique index
    op.execute("DROP INDEX IF EXISTS idx_conversations_url")

    # Restore the unique constraint on url
    op.execute("ALTER TABLE conversations ADD CONSTRAINT conversations_url_key UNIQUE (url)")

"""Add trigram indexes for summary and description

Revision ID: 0002
Revises: 0001
Create Date: 2025-09-11

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add trigram indexes to improve fuzzy matching on text fields."""
    # Ensure pg_trgm extension is available (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # conversations.summary trigram index
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_conversations_summary_trgm
        ON conversations USING GIN(summary gin_trgm_ops)
        """
    )

    # project_draft_versions.description trigram index
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_project_draft_versions_description_trgm
        ON project_draft_versions USING GIN(description gin_trgm_ops)
        """
    )


def downgrade() -> None:
    """Drop trigram indexes."""
    op.execute("DROP INDEX IF EXISTS idx_project_draft_versions_description_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_conversations_summary_trgm;")

"""
Add context planning columns to support summaries and chat digest.

Revision ID: 0004
Revises: 0003
Create Date: 2025-09-12
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # file_attachments: extracted_text, summary_text
    op.execute("ALTER TABLE file_attachments ADD COLUMN IF NOT EXISTS extracted_text TEXT")
    op.execute("ALTER TABLE file_attachments ADD COLUMN IF NOT EXISTS summary_text TEXT")

    # project_drafts: chat_digest, chat_digest_updated_at
    op.execute("ALTER TABLE project_drafts ADD COLUMN IF NOT EXISTS chat_digest TEXT")
    op.execute(
        "ALTER TABLE project_drafts ADD COLUMN IF NOT EXISTS chat_digest_updated_at TIMESTAMPTZ"
    )


def downgrade() -> None:
    # Safe to drop columns if exist
    op.execute("ALTER TABLE file_attachments DROP COLUMN IF EXISTS extracted_text")
    op.execute("ALTER TABLE file_attachments DROP COLUMN IF EXISTS summary_text")
    op.execute("ALTER TABLE project_drafts DROP COLUMN IF EXISTS chat_digest")
    op.execute("ALTER TABLE project_drafts DROP COLUMN IF EXISTS chat_digest_updated_at")

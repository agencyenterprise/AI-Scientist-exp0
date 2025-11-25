"""
Use chat_messages instead of imported_chat in dashboard view.

Revision ID: 0008
Revises: 0007
Create Date: 2025-09-16
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE VIEW conversation_dashboard_view AS
        SELECT
          c.id,
          c.url,
          c.title,
          c.import_date,
          c.is_locked,
          c.created_at,
          c.updated_at,
          u.id AS user_id,
          u.name AS user_name,
          u.email AS user_email,
          (
            SELECT pdv.title
            FROM project_drafts pd
            LEFT JOIN project_draft_versions pdv ON pd.active_version_id = pdv.id
            WHERE pd.conversation_id = c.id
            LIMIT 1
          ) AS project_draft_title,
          (
            SELECT pdv.description
            FROM project_drafts pd
            LEFT JOIN project_draft_versions pdv ON pd.active_version_id = pdv.id
            WHERE pd.conversation_id = c.id
            LIMIT 1
          ) AS project_draft_description,
          (
            SELECT p.linear_url
            FROM projects p
            WHERE p.conversation_id = c.id
            ORDER BY p.id DESC
            LIMIT 1
          ) AS linear_url,
          (
            SELECT cm.content
            FROM chat_messages cm
            JOIN project_drafts pd ON cm.project_draft_id = pd.id
            WHERE pd.conversation_id = c.id AND cm.role = 'user'
            ORDER BY cm.sequence_number DESC, cm.id DESC
            LIMIT 1
          ) AS last_user_message_content,
          (
            SELECT cm.content
            FROM chat_messages cm
            JOIN project_drafts pd ON cm.project_draft_id = pd.id
            WHERE pd.conversation_id = c.id AND cm.role = 'assistant'
            ORDER BY cm.sequence_number DESC, cm.id DESC
            LIMIT 1
          ) AS last_assistant_message_content
        FROM conversations c
        JOIN users u ON c.imported_by_user_id = u.id;
        """
    )


def downgrade() -> None:
    # Revert to previous definition that used imported_chat JSON if needed
    op.execute(
        """
        CREATE OR REPLACE VIEW conversation_dashboard_view AS
        SELECT
          c.id,
          c.url,
          c.title,
          c.import_date,
          c.is_locked,
          c.created_at,
          c.updated_at,
          u.id AS user_id,
          u.name AS user_name,
          u.email AS user_email,
          (
            SELECT pdv.title
            FROM project_drafts pd
            LEFT JOIN project_draft_versions pdv ON pd.active_version_id = pdv.id
            WHERE pd.conversation_id = c.id
            LIMIT 1
          ) AS project_draft_title,
          (
            SELECT pdv.description
            FROM project_drafts pd
            LEFT JOIN project_draft_versions pdv ON pd.active_version_id = pdv.id
            WHERE pd.conversation_id = c.id
            LIMIT 1
          ) AS project_draft_description,
          (
            SELECT p.linear_url
            FROM projects p
            WHERE p.conversation_id = c.id
            ORDER BY p.id DESC
            LIMIT 1
          ) AS linear_url,
          (
            SELECT elem->>'content'
            FROM jsonb_array_elements(c.imported_chat::jsonb) WITH ORDINALITY AS t(elem, ord)
            WHERE elem->>'role' = 'user'
            ORDER BY ord DESC
            LIMIT 1
          ) AS last_user_message_content,
          (
            SELECT elem->>'content'
            FROM jsonb_array_elements(c.imported_chat::jsonb) WITH ORDINALITY AS t(elem, ord)
            WHERE elem->>'role' = 'assistant'
            ORDER BY ord DESC
            LIMIT 1
          ) AS last_assistant_message_content
        FROM conversations c
        JOIN users u ON c.imported_by_user_id = u.id;
        """
    )

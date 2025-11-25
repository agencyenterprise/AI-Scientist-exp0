"""
Projects database operations.

Handles CRUD operations for projects table (Linear integration).
"""

import logging
from datetime import datetime
from typing import NamedTuple, Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


class ProjectData(NamedTuple):
    """Project data."""

    id: int
    conversation_id: int
    linear_project_id: str
    title: str
    description: str
    linear_url: str
    created_at: datetime


class ProjectsMixin:
    """Database operations for projects (Linear integration)."""

    def create_project(
        self,
        conversation_id: int,
        linear_project_id: str,
        title: str,
        description: str,
        linear_url: str,
        created_by_user_id: int,
    ) -> int:
        """Create a new project and lock the conversation. Returns project_id."""
        now = datetime.now()
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore[attr-defined]
            with conn.cursor() as cursor:
                # Create project
                cursor.execute(
                    """
                    INSERT INTO projects (conversation_id, linear_project_id, title, description, linear_url, created_at, created_by_user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        conversation_id,
                        linear_project_id,
                        title,
                        description,
                        linear_url,
                        now,
                        created_by_user_id,
                    ),
                )
                project_id: int = cursor.fetchone()[0]

                # Lock the conversation
                cursor.execute(
                    "UPDATE conversations SET is_locked = %s WHERE id = %s",
                    (True, conversation_id),
                )

                conn.commit()
                return project_id

    def get_project_by_conversation_id(self, conversation_id: int) -> Optional[ProjectData]:
        """Get project by conversation ID."""
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore[attr-defined]
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT id, conversation_id, linear_project_id, title, description, linear_url, created_at
                    FROM projects
                    WHERE conversation_id = %s
                """,
                    (conversation_id,),
                )
                result = cursor.fetchone()
                if not result:
                    return None

                return ProjectData(
                    id=result["id"],
                    conversation_id=result["conversation_id"],
                    linear_project_id=result["linear_project_id"],
                    title=result["title"],
                    description=result["description"],
                    linear_url=result["linear_url"],
                    created_at=result["created_at"],
                )

    def list_conversation_ids_by_linear_url(self, linear_url: str) -> list[int]:
        """Return conversation ids that have a project with the given linear_url."""
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore[attr-defined]
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT conversation_id
                    FROM projects
                    WHERE linear_url = %s
                    ORDER BY created_at DESC
                """,
                    (linear_url,),
                )
                rows = cursor.fetchall() or []
        return [int(r["conversation_id"]) for r in rows]

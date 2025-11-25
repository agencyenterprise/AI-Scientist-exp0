"""
Project drafts database operations.

Handles CRUD operations for project_drafts and project_draft_versions tables.
"""

import logging
from datetime import datetime
from typing import List, NamedTuple, Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


class ProjectDraftVersionData(NamedTuple):
    """Project draft version data."""

    version_id: int
    title: str
    description: str
    is_manual_edit: bool
    version_number: int
    created_at: datetime


class ProjectDraftData(NamedTuple):
    """Project draft data with active version."""

    project_draft_id: int
    conversation_id: int
    version_id: int
    title: str
    description: str
    version_number: int
    is_manual_edit: bool
    version_created_at: datetime
    created_at: datetime
    updated_at: datetime


class ProjectDraftsMixin:
    """Database operations for project drafts."""

    def create_project_draft(
        self,
        conversation_id: int,
        title: str,
        description: str,
        created_by_user_id: int,
    ) -> int:
        """Create a new project draft with initial version. Returns project_draft_id."""
        now = datetime.now()
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore
            with conn.cursor() as cursor:
                # Create project draft
                cursor.execute(
                    """
                    INSERT INTO project_drafts (conversation_id, created_at, updated_at, created_by_user_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """,
                    (conversation_id, now, now, created_by_user_id),
                )
                project_draft_id: int = cursor.fetchone()[0]

                # Create initial version
                cursor.execute(
                    """
                    INSERT INTO project_draft_versions
                    (project_draft_id, title, description, is_manual_edit, version_number, created_at, created_by_user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (project_draft_id, title, description, False, 1, now, created_by_user_id),
                )
                version_id: int = cursor.fetchone()[0]

                # Set as active version
                cursor.execute(
                    "UPDATE project_drafts SET active_version_id = %s, updated_at = %s WHERE id = %s",
                    (version_id, now, project_draft_id),
                )

                conn.commit()
                return project_draft_id

    def get_project_draft_by_conversation_id(
        self, conversation_id: int
    ) -> Optional[ProjectDraftData]:
        """Get project draft with active version for a conversation."""
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT
                        pd.id as project_draft_id,
                        pd.conversation_id,
                        pdv.id as version_id,
                        pdv.title,
                        pdv.description,
                        pdv.version_number,
                        pdv.is_manual_edit,
                        pdv.created_at as version_created_at,
                        pd.created_at,
                        pd.updated_at
                    FROM project_drafts pd
                    LEFT JOIN project_draft_versions pdv ON pd.active_version_id = pdv.id
                    WHERE pd.conversation_id = %s
                """,
                    (conversation_id,),
                )
                result = cursor.fetchone()
                return ProjectDraftData(**result) if result else None

    def update_project_draft_version(
        self,
        project_draft_id: int,
        version_id: int,
        title: str,
        description: str,
        is_manual_edit: bool,
    ) -> bool:
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE project_draft_versions SET title = %s, description = %s, is_manual_edit = %s WHERE id = %s AND project_draft_id = %s",
                    (title, description, is_manual_edit, version_id, project_draft_id),
                )
                conn.commit()
                return bool(cursor.rowcount > 0)

    def create_project_draft_version(
        self,
        project_draft_id: int,
        title: str,
        description: str,
        is_manual_edit: bool,
        created_by_user_id: int,
    ) -> int:
        """Create a new version of a project draft. Returns version_id."""
        now = datetime.now()
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore
            with conn.cursor() as cursor:
                # Get next version number
                cursor.execute(
                    "SELECT COALESCE(MAX(version_number), 0) + 1 FROM project_draft_versions WHERE project_draft_id = %s",
                    (project_draft_id,),
                )
                next_version = cursor.fetchone()[0]

                # Create new version
                cursor.execute(
                    """
                    INSERT INTO project_draft_versions
                    (project_draft_id, title, description, is_manual_edit, version_number, created_at, created_by_user_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        project_draft_id,
                        title,
                        description,
                        is_manual_edit,
                        next_version,
                        now,
                        created_by_user_id,
                    ),
                )
                version_id: int = cursor.fetchone()[0]

                # Update active version and project draft timestamp
                cursor.execute(
                    "UPDATE project_drafts SET active_version_id = %s, updated_at = %s WHERE id = %s",
                    (version_id, now, project_draft_id),
                )

                conn.commit()
                return version_id

    def get_project_draft_versions(self, project_draft_id: int) -> List[ProjectDraftVersionData]:
        """Get all versions of a project draft, ordered by version number desc."""
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT
                        id as version_id,
                        title,
                        description,
                        is_manual_edit,
                        version_number,
                        created_at
                    FROM project_draft_versions
                    WHERE project_draft_id = %s
                    ORDER BY version_number DESC
                """,
                    (project_draft_id,),
                )
                results = cursor.fetchall()
                return [ProjectDraftVersionData(**row) for row in results]

    def get_project_draft_by_id(self, project_draft_id: int) -> Optional[ProjectDraftData]:
        """Get a project draft with its active version by project_draft id."""
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT
                        pd.id as project_draft_id,
                        pd.conversation_id,
                        pdv.id as version_id,
                        pdv.title,
                        pdv.description,
                        pdv.version_number,
                        pdv.is_manual_edit,
                        pdv.created_at as version_created_at,
                        pd.created_at,
                        pd.updated_at
                    FROM project_drafts pd
                    LEFT JOIN project_draft_versions pdv ON pd.active_version_id = pdv.id
                    WHERE pd.id = %s
                    """,
                    (project_draft_id,),
                )
                result = cursor.fetchone()
                return ProjectDraftData(**result) if result else None

    def set_active_project_draft_version(self, project_draft_id: int, version_id: int) -> bool:
        """Set a specific version as the active version for a project draft."""
        now = datetime.now()
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE project_drafts SET active_version_id = %s, updated_at = %s WHERE id = %s",
                    (version_id, now, project_draft_id),
                )
                conn.commit()
                return bool(cursor.rowcount > 0)

    def recover_project_draft_version(
        self, project_draft_id: int, source_version_id: int, created_by_user_id: int
    ) -> Optional[int]:
        """Create a new version by copying data from an existing version.

        This is used when "recovering" an older version - instead of just reactivating
        the old version, we create a new version with the same content to preserve history.

        Returns the new version ID if successful, None otherwise.
        """
        now = datetime.now()
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore
            with conn.cursor() as cursor:
                # Get the source version data
                cursor.execute(
                    """SELECT title, description, is_manual_edit
                       FROM project_draft_versions
                       WHERE id = %s AND project_draft_id = %s""",
                    (source_version_id, project_draft_id),
                )
                source_version = cursor.fetchone()

                if not source_version:
                    return None

                title, description, is_manual_edit = source_version

                # Get the next version number
                cursor.execute(
                    "SELECT COALESCE(MAX(version_number), 0) + 1 FROM project_draft_versions WHERE project_draft_id = %s",
                    (project_draft_id,),
                )
                next_version_number = cursor.fetchone()[0]

                # Create the new version with copied data
                cursor.execute(
                    """INSERT INTO project_draft_versions
                       (project_draft_id, title, description, is_manual_edit, version_number, created_at, created_by_user_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (
                        project_draft_id,
                        title,
                        description,
                        is_manual_edit,
                        next_version_number,
                        now,
                        created_by_user_id,
                    ),
                )
                new_version_id: int = cursor.fetchone()[0]

                # Set this new version as the active version
                cursor.execute(
                    "UPDATE project_drafts SET active_version_id = %s, updated_at = %s WHERE id = %s",
                    (new_version_id, now, project_draft_id),
                )

                conn.commit()
                return new_version_id

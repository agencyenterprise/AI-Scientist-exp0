"""
Search chunks database operations.

Provides CRUD helpers for the unified search_chunks table.
"""

from datetime import datetime
from typing import List, Literal, NamedTuple, Optional

import psycopg2


def _to_vector_literal(embedding: List[float]) -> str:
    return "[" + ",".join(repr(x) for x in embedding) + "]"


class GroupedConversationSearchRow(NamedTuple):
    content_type: Literal["imported_chat", "draft_chat", "project_draft"]
    conversation_id: int
    snippet: str
    score: float
    conversation_title: str
    created_at: datetime
    updated_at: datetime
    import_date: datetime
    user_name: str
    user_email: str
    total_conversations: int
    conv_rank: int


class SearchChunksMixin:
    """Database operations for search_chunks."""

    class SearchChunkSearchRow(NamedTuple):
        source_type: str
        conversation_id: int
        chat_message_id: Optional[int]
        project_draft_id: Optional[int]
        project_draft_version_id: Optional[int]
        message_index: Optional[int]
        sequence_number: Optional[int]
        chunk_index: int
        text: str
        score: float

    def delete_imported_chat_chunks(self, conversation_id: int) -> None:
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore[attr-defined]
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM search_chunks WHERE source_type = 'imported_chat' AND conversation_id = %s",
                    (conversation_id,),
                )
                conn.commit()

    def insert_imported_chat_chunk(
        self,
        conversation_id: int,
        message_index: int,
        chunk_index: int,
        text: str,
        embedding: List[float],
    ) -> None:
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore[attr-defined]
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO search_chunks
                    (source_type, conversation_id, message_index, chunk_index, text, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s::vector)
                    """,
                    (
                        "imported_chat",
                        conversation_id,
                        message_index,
                        chunk_index,
                        text,
                        _to_vector_literal(embedding),
                    ),
                )
                conn.commit()

    def delete_draft_chat_chunks_by_message(self, chat_message_id: int) -> None:
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore[attr-defined]
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM search_chunks WHERE source_type = 'draft_chat' AND chat_message_id = %s",
                    (chat_message_id,),
                )
                conn.commit()

    def insert_draft_chat_chunk(
        self,
        conversation_id: int,
        project_draft_id: int,
        project_draft_version_id: int,
        chat_message_id: int,
        sequence_number: int,
        chunk_index: int,
        text: str,
        embedding: List[float],
    ) -> None:
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore[attr-defined]
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO search_chunks
                    (source_type, conversation_id, project_draft_id, project_draft_version_id, chat_message_id, sequence_number, chunk_index, text, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                    """,
                    (
                        "draft_chat",
                        conversation_id,
                        project_draft_id,
                        project_draft_version_id,
                        chat_message_id,
                        sequence_number,
                        chunk_index,
                        text,
                        _to_vector_literal(embedding),
                    ),
                )
                conn.commit()

    def delete_project_draft_chunks(self, project_draft_id: int) -> None:
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore[attr-defined]
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM search_chunks WHERE source_type = 'project_draft' AND project_draft_id = %s",
                    (project_draft_id,),
                )
                conn.commit()

    def insert_project_draft_chunk(
        self,
        conversation_id: int,
        project_draft_id: int,
        project_draft_version_id: int,
        chunk_index: int,
        text: str,
        embedding: List[float],
    ) -> None:
        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore[attr-defined]
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO search_chunks
                    (source_type, conversation_id, project_draft_id, project_draft_version_id, chunk_index, text, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                    """,
                    (
                        "project_draft",
                        conversation_id,
                        project_draft_id,
                        project_draft_version_id,
                        chunk_index,
                        text,
                        _to_vector_literal(embedding),
                    ),
                )
                conn.commit()

    def search_grouped_conversations(
        self,
        query_vector: List[float],
        status: str,
        sort_by: str,
        sort_dir: str,
        limit: int,
        offset: int,
    ) -> List[GroupedConversationSearchRow]:
        """Return best-per-type rows grouped by conversation, ordered and paginated at the SQL level.

        - Groups chunk-level matches to conversation-level using conversation_id (NOT NULL)
        - Picks top row per conversation per source_type by vector distance
        - Ranks conversations by earliest chunk rank (conv_rank) and aggregates max score (conv_score)
        - Applies status filtering on conversations (all | completed | in_progress)
        - Orders conversations by requested sort (relevance|score|title|imported|updated) and direction
        - Returns rows for visible conversations only (LIMIT/OFFSET), including a total count
        """
        sql = """
        WITH base AS (
            SELECT
                sc.source_type,
                sc.conversation_id AS conversation_id,
                sc.text,
                sc.embedding
            FROM search_chunks sc
        ),
        scored AS (
            SELECT
                source_type,
                conversation_id,
                text,
                (1 - (embedding <=> %s::vector)) AS score,
                ROW_NUMBER() OVER (
                    PARTITION BY conversation_id, source_type
                    ORDER BY embedding <=> %s::vector
                ) AS rn,
                ROW_NUMBER() OVER (
                    PARTITION BY conversation_id
                    ORDER BY embedding <=> %s::vector
                ) AS conv_rn
            FROM base
        ),
        best_per_type AS (
            SELECT
                source_type,
                conversation_id,
                text,
                score,
                MIN(conv_rn) OVER (PARTITION BY conversation_id) AS conv_rank
            FROM scored
            WHERE rn = 1 AND score >= 0.25
        ),
        conv_ranked AS (
            SELECT
                conversation_id,
                MAX(score) AS conv_score,
                MIN(conv_rank) AS conv_rank
            FROM best_per_type
            GROUP BY conversation_id
        ),
        eligible AS (
            SELECT
                c.id AS conversation_id,
                c.title AS conversation_title,
                c.created_at AS created_at,
                c.updated_at AS updated_at,
                c.import_date AS import_date,
                u.name AS user_name,
                u.email AS user_email,
                cr.conv_rank AS conv_rank,
                cr.conv_score AS conv_score
            FROM conv_ranked cr
            JOIN conversations c ON c.id = cr.conversation_id
            JOIN users u ON u.id = c.imported_by_user_id
            WHERE (
                CASE
                    WHEN %s = 'all' THEN TRUE
                    WHEN %s = 'completed' THEN c.is_locked = TRUE
                    ELSE c.is_locked = FALSE
                END
            )
        ),
        eligible_count AS (
            SELECT COUNT(*) AS total_conversations FROM eligible
        ),
        ordered_conversations AS (
            SELECT e.*, ec.total_conversations
            FROM eligible e
            CROSS JOIN eligible_count ec
            ORDER BY
                CASE WHEN %s = 'relevance' AND %s = 'desc' THEN e.conv_rank END ASC,
                CASE WHEN %s = 'relevance' AND %s = 'asc' THEN e.conv_rank END DESC,
                CASE WHEN %s = 'score' AND %s = 'desc' THEN e.conv_score END DESC,
                CASE WHEN %s = 'score' AND %s = 'asc' THEN e.conv_score END ASC,
                CASE WHEN %s = 'title' AND %s = 'desc' THEN e.conversation_title END DESC,
                CASE WHEN %s = 'title' AND %s = 'asc' THEN e.conversation_title END ASC,
                CASE WHEN %s = 'imported' AND %s = 'desc' THEN e.import_date END DESC,
                CASE WHEN %s = 'imported' AND %s = 'asc' THEN e.import_date END ASC,
                CASE WHEN %s = 'updated' AND %s = 'desc' THEN e.updated_at END DESC,
                CASE WHEN %s = 'updated' AND %s = 'asc' THEN e.updated_at END ASC,
                e.conv_rank ASC
            LIMIT %s OFFSET %s
        )
        SELECT
            bpt.source_type AS content_type,
            bpt.conversation_id,
            bpt.text AS snippet,
            bpt.score,
            oc.conversation_title,
            oc.created_at,
            oc.updated_at,
            oc.import_date,
            oc.user_name,
            oc.user_email,
            oc.total_conversations,
            oc.conv_rank
        FROM best_per_type bpt
        JOIN ordered_conversations oc ON oc.conversation_id = bpt.conversation_id
        ORDER BY
            CASE WHEN %s = 'relevance' AND %s = 'desc' THEN oc.conv_rank END ASC,
            CASE WHEN %s = 'relevance' AND %s = 'asc' THEN oc.conv_rank END DESC,
            CASE WHEN %s = 'score' AND %s = 'desc' THEN oc.conv_score END DESC,
            CASE WHEN %s = 'score' AND %s = 'asc' THEN oc.conv_score END ASC,
            CASE WHEN %s = 'title' AND %s = 'desc' THEN oc.conversation_title END DESC,
            CASE WHEN %s = 'title' AND %s = 'asc' THEN oc.conversation_title END ASC,
            CASE WHEN %s = 'imported' AND %s = 'desc' THEN oc.import_date END DESC,
            CASE WHEN %s = 'imported' AND %s = 'asc' THEN oc.import_date END ASC,
            CASE WHEN %s = 'updated' AND %s = 'desc' THEN oc.updated_at END DESC,
            CASE WHEN %s = 'updated' AND %s = 'asc' THEN oc.updated_at END ASC,
            oc.conv_rank ASC, bpt.score DESC, bpt.source_type
        """

        vector_literal = _to_vector_literal(embedding=query_vector)
        params: List[object] = [vector_literal, vector_literal, vector_literal]

        # status appears twice in eligible filter
        params.extend([status, status])

        # sort_by and sort_dir pairs repeated for each CASE in ORDER BY
        pairs = [
            (sort_by, sort_dir),  # relevance desc
            (sort_by, sort_dir),  # relevance asc
            (sort_by, sort_dir),  # score desc
            (sort_by, sort_dir),  # score asc
            (sort_by, sort_dir),  # title desc
            (sort_by, sort_dir),  # title asc
            (sort_by, sort_dir),  # imported desc
            (sort_by, sort_dir),  # imported asc
            (sort_by, sort_dir),  # updated desc
            (sort_by, sort_dir),  # updated asc
        ]
        for by, direction in pairs:
            params.append(by)
            params.append(direction)

        params.extend([limit, offset])

        # Repeat sort pairs for the final ORDER BY to preserve requested ordering
        for by, direction in pairs:
            params.append(by)
            params.append(direction)

        with psycopg2.connect(**self.pg_config) as conn:  # type: ignore[attr-defined]
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()

        grouped: List[GroupedConversationSearchRow] = []
        for row in rows:
            grouped.append(
                GroupedConversationSearchRow(
                    content_type=row[0],
                    conversation_id=int(row[1]),
                    snippet=row[2],
                    score=float(row[3]),
                    conversation_title=row[4],
                    created_at=row[5],
                    updated_at=row[6],
                    import_date=row[7],
                    user_name=row[8],
                    user_email=row[9],
                    total_conversations=int(row[10]),
                    conv_rank=int(row[11]),
                )
            )
        return grouped

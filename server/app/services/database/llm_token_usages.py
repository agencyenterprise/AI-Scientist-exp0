"""
LLM token usage database operations.

Handles operations for llm_token_usages table.
"""

import logging
from datetime import datetime
from typing import NamedTuple, Optional

import psycopg2
import psycopg2.extras

from .base import ConnectionProvider

logger = logging.getLogger(__name__)


class LlmTokenUsage(NamedTuple):
    """Represents a record of LLM token usage."""

    id: int
    conversation_id: int
    run_id: Optional[str]
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    created_at: datetime
    updated_at: datetime


class LlmTokenUsagesMixin(ConnectionProvider):
    """Database operations for LLM token usages."""

    def create_llm_token_usage(
        self,
        conversation_id: int,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        run_id: Optional[str] = None,
    ) -> int:
        """Create a new LLM token usage record in the database."""
        now = datetime.now()

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    INSERT INTO llm_token_usages
                    (conversation_id, run_id, provider, model, input_tokens, output_tokens, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        conversation_id,
                        run_id,
                        provider,
                        model,
                        input_tokens,
                        output_tokens,
                        now,
                        now,
                    ),
                )
                result = cursor.fetchone()
                if not result:
                    raise ValueError("Failed to create LLM token usage record: no ID returned")

                token_usage_id = int(result["id"])
                conn.commit()

        return token_usage_id

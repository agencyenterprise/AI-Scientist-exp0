import logging
import os
import traceback
from collections import defaultdict
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar
from uuid import UUID

import psycopg2
from langchain.chat_models import BaseChatModel
from langchain.chat_models.base import _parse_model
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from ai_scientist.telemetry.event_persistence import _parse_database_url


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Environment variable {name} is required")
    return value


database_url = _require_env("DATABASE_PUBLIC_URL")
RUN_ID = _require_env("RUN_ID")
pg_config = _parse_database_url(database_url)


def create_db_cost_track(
    model: str,
    *,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    ai_message: AIMessage | None = None,
    run_id: str | None = None,
) -> None:
    if run_id is None:
        run_id = RUN_ID
    if (input_tokens is None or output_tokens is None) and ai_message is None:
        raise ValueError("Either input_tokens and output_tokens or ai_message must be provided")
    if ai_message:
        usage_metadata = ai_message.usage_metadata
        if input_tokens is None and usage_metadata:
            input_tokens = int(usage_metadata.get("input_tokens", 0) or 0)
        if output_tokens is None and usage_metadata:
            output_tokens = int(usage_metadata.get("output_tokens", 0) or 0)

    provider, model_name = extract_model_name_and_provider(model)
    now = datetime.now()
    with psycopg2.connect(**pg_config) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO llm_token_usages (
                    conversation_id,
                    run_id,
                    provider,
                    model,
                    input_tokens,
                    output_tokens,
                    created_at,
                    updated_at
                )
                SELECT
                    i.conversation_id, 
                    rpr.run_id,
                    %s AS provider,
                    %s AS model,
                    %s AS input_tokens,
                    %s AS output_tokens,
                    %s AS created_at,
                    %s AS updated_at
                FROM research_pipeline_runs rpr 
                INNER JOIN ideas i 
                    ON i.id=rpr.idea_id 
                WHERE rpr.id = %s 
                LIMIT 1
                """,
                (
                    provider,
                    model_name,
                    input_tokens,
                    output_tokens,
                    now,
                    now,
                    run_id,
                ),
            )
            conn.commit()


class TrackCostCallbackHandler(BaseCallbackHandler):
    def __init__(self, model: str | None = None):
        self.model = model

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,  # noqa: ARG002
        parent_run_id: UUID | None = None,  # noqa: ARG002
        **kwargs: Any,  # noqa: ANN401, ARG002
    ) -> Any:  # noqa: ANN401
        try:
            if not response.generations:
                return
            generation = response.generations[0]
            if not generation:
                return
            last_generation = generation[0]
            if not last_generation:
                return
            if not isinstance(last_generation, ChatGeneration):
                return
            message = last_generation.message
            if isinstance(message, AIMessage):
                model_name = self.model or message.response_metadata.get("model_name")
                if not model_name:
                    raise ValueError(
                        "Model name not found in response metadata or provided in constructor"
                    )
                create_db_cost_track(
                    model=model_name,
                    ai_message=message,
                )
        except Exception:
            traceback.print_exc()
            logging.warning("Token tracking failed; continuing without tracking")


def extract_model_name_and_provider(model: str | BaseChatModel) -> tuple[str, str]:
    if isinstance(model, BaseChatModel):
        if hasattr(model, "model"):
            model_name = model.model
        elif hasattr(model, "model_name"):
            model_name = model.model_name
        else:
            raise ValueError(f"Model {model} has no model or model_name attribute")
    else:
        model_name = model
    return _parse_model(model_name, None)


class TokenTracker:
    def __init__(self) -> None:
        """
        Token counts for prompt, completion, reasoning, and cached.
        Reasoning tokens are included in completion tokens.
        Cached tokens are included in prompt tokens.
        Also tracks prompts, responses, and timestamps.
        We assume we get these from the LLM response, and we don't count
        the tokens by ourselves.
        """
        self.token_counts: dict[str, dict[str, int]] = defaultdict(
            lambda: {"prompt": 0, "completion": 0, "reasoning": 0, "cached": 0}
        )
        self.interactions: dict[str, list] = defaultdict(list)

    def add_tokens(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        reasoning_tokens: int,
        cached_tokens: int,
    ) -> None:
        self.token_counts[model]["prompt"] += prompt_tokens
        self.token_counts[model]["completion"] += completion_tokens
        self.token_counts[model]["reasoning"] += reasoning_tokens
        self.token_counts[model]["cached"] += cached_tokens

    def add_interaction(
        self,
        model: str,
        system_message: str,
        prompt: str,
        response: str,
        timestamp: datetime,
    ) -> None:
        """Record a single interaction with the model."""
        self.interactions[model].append(
            {
                "system_message": system_message,
                "prompt": prompt,
                "response": response,
                "timestamp": timestamp,
            }
        )

    def get_interactions(self, model: Optional[str] = None) -> Dict[str, List[Dict]]:
        """Get all interactions, optionally filtered by model."""
        if model:
            return {
                model: [
                    self._json_safe_interaction(interaction=i) for i in self.interactions[model]
                ]
            }
        return {
            m: [self._json_safe_interaction(interaction=i) for i in interactions]
            for m, interactions in self.interactions.items()
        }

    def reset(self) -> None:
        """Reset all token counts and interactions."""
        self.token_counts = defaultdict(
            lambda: {"prompt": 0, "completion": 0, "reasoning": 0, "cached": 0}
        )
        self.interactions = defaultdict(list)
        # self._encoders = {}

    def get_summary(self) -> dict[str, dict[str, int]]:
        """Get summary of token usage for all models."""
        summary: dict[str, dict[str, int]] = {}
        for model, tokens in self.token_counts.items():
            summary[model] = {k: v for k, v in tokens.items()}
        return summary

    def _json_safe_interaction(self, *, interaction: Dict[str, Any]) -> Dict[str, Any]:
        safe: Dict[str, Any] = dict(interaction)
        ts = safe.get("timestamp")
        if isinstance(ts, datetime):
            safe["timestamp"] = ts.isoformat()
        elif ts is not None:
            safe["timestamp"] = str(ts)
        else:
            safe["timestamp"] = None
        return safe


# Global token tracker instance
token_tracker = TokenTracker()


T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


def track_token_usage(func: F) -> F:
    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> object:
        result = func(*args, **kwargs)

        try:
            model_obj = kwargs.get("model", "unknown-model")
            model = str(model_obj)
            prompt = str(kwargs.get("prompt") or "")
            system_message = str(kwargs.get("system_message") or "")
            timestamp = datetime.utcnow()

            usage_md = getattr(result, "usage_metadata", {}) or {}
            prompt_tokens = int(usage_md.get("input_tokens", 0) or 0)
            completion_tokens = int(usage_md.get("output_tokens", 0) or 0)
            reasoning_tokens = int(usage_md.get("reasoning_tokens", 0) or 0)
            cached_tokens = int(usage_md.get("cached_tokens", 0) or 0)

            token_tracker.add_tokens(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                reasoning_tokens=reasoning_tokens,
                cached_tokens=cached_tokens,
            )

            response_text = ""
            try:
                # AIMessage.content can be text or a list of blocks; str(...) is robust.
                response_text = str(getattr(result, "content", ""))
            except Exception:
                # Best effort; do not fail if response shape differs
                pass

            token_tracker.add_interaction(
                model=model,
                system_message=str(system_message),
                prompt=str(prompt),
                response=response_text,
                timestamp=timestamp,
            )
        except Exception:
            traceback.print_exc()
            logging.warning("Token tracking failed; continuing without tracking")
        return result

    return wrapper  # type: ignore[return-value]

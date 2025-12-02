"""
Shared helpers for LLM-powered summarization.

Keeping these utilities in this module ensures that low-level LLM construction
remains centralized rather than scattered across the codebase.
"""

from __future__ import annotations

import logging
from typing import List, Sequence, Tuple, Union

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.config import settings
from app.models import ChatMessageData, ImportedChatMessage
from app.services.base_llm_service import BaseLLMService
from app.services.database import DatabaseManager

logger = logging.getLogger(__name__)

MessageLike = Union[ChatMessageData, ImportedChatMessage]

SUMMARY_CHAR_BUDGET = 8_000
MIN_LIVE_MESSAGES_FOR_SUMMARY = 20
LIVE_RECENT_MESSAGE_LIMIT = 6
SUMMARY_MODEL_ID = "gpt-5-nano"
SUMMARY_COMPLETION_TOKENS = min(settings.IDEA_MAX_COMPLETION_TOKENS, 1_024)
SUMMARY_SYSTEM_PROMPT = (
    "You condense lengthy research chats into concise, factual summaries. "
    "Capture objectives, experiments, blockers, explicit decisions, and open questions. "
    "Preserve terminology and participants. Stay neutral and avoid hallucinating details."
)


async def summarize_live_chat_history(
    chat_history: List[ChatMessageData],
    *,
    min_messages: int = MIN_LIVE_MESSAGES_FOR_SUMMARY,
    recent_limit: int = LIVE_RECENT_MESSAGE_LIMIT,
) -> Tuple[Union[str, None], List[ChatMessageData]]:
    """Return a tuple of (summary text or None, recent tail messages)."""
    if len(chat_history) < min_messages:
        return None, chat_history

    head = chat_history[:-recent_limit] if len(chat_history) > recent_limit else chat_history
    tail = chat_history[-recent_limit:] if recent_limit else chat_history
    summary_text = await summarize_messages(head)
    return summary_text or None, tail


async def summarize_and_store_imported_chat(
    db: DatabaseManager,
    conversation_id: int,
    messages: List[ImportedChatMessage],
) -> str:
    """Summarize imported chat messages and persist them for prompt building."""
    summary_text = await summarize_messages(messages)
    existing = db.get_imported_conversation_summary_by_conversation_id(conversation_id)
    if existing:
        db.update_imported_conversation_summary(conversation_id, summary_text)
    else:
        db.create_imported_conversation_summary(
            conversation_id=conversation_id,
            external_id=0,
            summary=summary_text,
        )
    return summary_text


async def summarize_messages(messages: Sequence[MessageLike]) -> str:
    transcript = _messages_to_text(messages)
    if not transcript:
        return ""
    if len(transcript) <= SUMMARY_CHAR_BUDGET:
        return await _invoke_summary(transcript)

    chunks = _chunk_text(transcript)
    chunk_summaries = [await _invoke_summary(chunk) for chunk in chunks]
    combined = "\n\n".join(filter(None, chunk_summaries)).strip()
    if len(combined) <= SUMMARY_CHAR_BUDGET:
        return await _invoke_summary(combined)
    # Final compression pass if still too long.
    return await _invoke_summary(combined[: SUMMARY_CHAR_BUDGET * 2])


async def _invoke_summary(transcript: str) -> str:
    client = _build_summary_client()
    try:
        response: AIMessage = await client.ainvoke(
            [
                SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
                HumanMessage(content=_build_user_prompt(transcript)),
            ],
            max_tokens=SUMMARY_COMPLETION_TOKENS,
        )
    except Exception:
        logger.exception("Failed to summarize transcript; returning truncated text.")
        return transcript[:SUMMARY_CHAR_BUDGET]

    content = response.content if isinstance(response.content, str) else str(response.content)
    return content.strip()


def _build_summary_client() -> ChatOpenAI:
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY must be configured for summarization.")
    return ChatOpenAI(
        model=SUMMARY_MODEL_ID,
        api_key=SecretStr(api_key),
        temperature=0,
        streaming=False,
    )


def _chunk_text(text: str) -> List[str]:
    chunks = BaseLLMService.split_text_to_fit_char_budget(
        text=text,
        max_chars=SUMMARY_CHAR_BUDGET,
    )
    return [chunk for chunk in chunks if chunk]


def _messages_to_text(messages: Sequence[MessageLike]) -> str:
    segments: List[str] = []
    for message in messages:
        role = getattr(message, "role", "user").lower()
        if role == "user":
            prefix = "User"
        elif role == "assistant":
            prefix = "Assistant"
        else:
            prefix = role.title()
        content = getattr(message, "content", "")
        if not isinstance(content, str):
            content = str(content)
        segments.append(f"{prefix}: {content}".strip())
    return "\n\n".join(segments).strip()


def _build_user_prompt(transcript: str) -> str:
    return (
        "Conversation transcript:\n"
        f"{transcript}\n\n"
        "Write a summary (<350 words) that a collaborator can use to rejoin the project."
    )

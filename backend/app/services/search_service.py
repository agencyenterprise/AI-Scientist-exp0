"""
Search service.

Provides:
- Chunk-level vector search over unified search_chunks (for internal tests)
- Conversation-level grouped search with ordering, pagination, and exact URL injection
"""

import re
from typing import List, Literal, NamedTuple

from app.services.database import DatabaseManager, get_database
from app.services.embeddings_service import EmbeddingsService

SearchScope = Literal["imported_chat", "draft_chat", "project_draft"]


class BaseResult(NamedTuple):
    source_type: SearchScope
    snippet: str
    score: float


class ImportedChatResult(NamedTuple):
    source_type: Literal["imported_chat"]
    conversation_id: int
    message_index: int
    chunk_index: int
    snippet: str
    score: float


class DraftChatResult(NamedTuple):
    source_type: Literal["draft_chat"]
    project_draft_id: int
    project_draft_version_id: int
    chat_message_id: int
    sequence_number: int
    chunk_index: int
    snippet: str
    score: float


class ProjectDraftResult(NamedTuple):
    source_type: Literal["project_draft"]
    project_draft_id: int
    project_draft_version_id: int
    chunk_index: int
    snippet: str
    score: float


SearchResult = ImportedChatResult | DraftChatResult | ProjectDraftResult


class SearchService:
    """Service for performing vector search with pgvector."""

    def __init__(self) -> None:
        self._db: DatabaseManager = get_database()
        self._score_threshold: float = 0.25  # drop weak matches
        self._embeddings: EmbeddingsService = EmbeddingsService()
        self._snippet_max_length: int = 320

    # ======================================================================
    # Conversation-level grouped search API (for FastAPI layer)
    # ======================================================================

    class ConversationSearchItem(NamedTuple):
        content_type: Literal["conversation", "imported_chat", "draft_chat", "project_draft"]
        conversation_id: int
        content_snippet: str
        score: float
        created_at: str
        conversation_title: str
        created_by_user_name: str
        created_by_user_email: str

    class ConversationSearchResult(NamedTuple):
        items: List["SearchService.ConversationSearchItem"]
        total_conversations: int
        has_more: bool

    def search_conversations(
        self,
        query: str,
        limit: int,
        offset: int,
        status: Literal["all", "in_progress", "completed"],
        sort_by: Literal["updated", "imported", "title", "relevance", "score"],
        sort_dir: Literal["asc", "desc"],
    ) -> "SearchService.ConversationSearchResult":
        trimmed_query = query.strip()
        query_embedding = self._embeddings.embed_texts(texts=[trimmed_query])[0]

        # Detect exact share URL match by extracting provider-specific IDs and canonicalizing
        exact_conversation_ids: List[int] = []

        # ChatGPT UUID
        uuid_match = re.search(
            r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
            trimmed_query,
            re.IGNORECASE,
        )
        if uuid_match:
            uuid_str = uuid_match.group(0).lower()
            canonical_url = f"https://chatgpt.com/share/{uuid_str}"
            matches = self._db.list_conversations_by_url(url=canonical_url)
            for match in matches:
                exact_conversation_ids.append(int(match.id))

        # BranchPrompt 24-hex id
        bp_match = re.search(r"\b[a-f0-9]{24}\b", trimmed_query)
        if bp_match:
            bp_id = bp_match.group(0).lower()
            canonical_bp_url = f"https://v2.branchprompt.com/conversation/{bp_id}"
            matches = self._db.list_conversations_by_url(url=canonical_bp_url)
            for match in matches:
                exact_conversation_ids.append(int(match.id))

        # Claude share UUID (same uuid as ChatGPT; detect full claude.ai URL or id)
        claude_url_match = re.search(
            r"https://claude\.ai/share/([a-f0-9\-]{36})", trimmed_query, re.IGNORECASE
        )
        if claude_url_match:
            cid = claude_url_match.group(1).lower()
            canonical_claude_url = f"https://claude.ai/share/{cid}"
            matches = self._db.list_conversations_by_url(url=canonical_claude_url)
            for match in matches:
                exact_conversation_ids.append(int(match.id))

        # Grok share token (base64-like or percent-encoded prefix + uuid). Prefer matching full URL
        grok_url_match = re.search(
            r"https://grok\.com/share/([A-Za-z0-9_%\-]+_[a-f0-9\-]{36})",
            trimmed_query,
            re.IGNORECASE,
        )
        if grok_url_match:
            gid = grok_url_match.group(1)
            canonical_grok_url = f"https://grok.com/share/{gid}"
            matches = self._db.list_conversations_by_url(url=canonical_grok_url)
            for match in matches:
                exact_conversation_ids.append(int(match.id))

        # Detect Linear project URL exact match
        project_conversation_ids: List[int] = []
        linear_urls = re.findall(r"https://linear\.app/\S+", trimmed_query)
        if linear_urls:
            seen_ids = set()
            for linear_url in linear_urls:
                ids = self._db.list_conversation_ids_by_linear_url(linear_url=linear_url)
                for cid in ids:
                    if cid not in seen_ids:
                        project_conversation_ids.append(cid)
                        seen_ids.add(cid)

        # Grouped, ordered, paginated rows from SQL
        grouped_rows = self._db.search_grouped_conversations(
            query_vector=query_embedding,
            status=status,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )

        present_conversation_ids = {int(r.conversation_id) for r in grouped_rows}

        # Convert grouped rows to items
        base_items: List[SearchService.ConversationSearchItem] = []
        for row in grouped_rows:
            truncated = self._truncate_snippet(
                snippet=row.snippet, query=trimmed_query, max_length=self._snippet_max_length
            )
            base_items.append(
                SearchService.ConversationSearchItem(
                    content_type=row.content_type,
                    conversation_id=int(row.conversation_id),
                    content_snippet=truncated,
                    score=float(row.score),
                    created_at=row.created_at.isoformat(),
                    conversation_title=row.conversation_title,
                    created_by_user_name=row.user_name,
                    created_by_user_email=row.user_email,
                )
            )

        # Build injection items: title substring/prefix first, then URL exact
        injected_count = 0
        injected_unique_ids = set()  # for counting only
        items: List[SearchService.ConversationSearchItem] = []

        # Title substring/prefix injection (before URL injection)
        title_injections: List[SearchService.ConversationSearchItem] = []
        # Extract title query by removing any share UUID from the query (supports "frag <uuid>")
        title_query = re.sub(
            pattern=r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
            repl="",
            string=trimmed_query,
            flags=re.IGNORECASE,
        ).strip()
        if title_query:
            title_matches = self._db.list_conversations_by_title_substring(title_query=title_query)
            for m in title_matches:
                conv = self._db.get_conversation_by_id(conversation_id=int(m.id))
                if not conv:
                    continue
                title_injections.append(
                    SearchService.ConversationSearchItem(
                        content_type="conversation",
                        conversation_id=int(m.id),
                        content_snippet=f"Exact title match: {conv.title}",
                        score=1.0,
                        created_at=conv.created_at.isoformat(),
                        conversation_title=conv.title,
                        created_by_user_name=conv.user_name,
                        created_by_user_email=conv.user_email,
                    )
                )
                if (
                    int(m.id) not in present_conversation_ids
                    and int(m.id) not in injected_unique_ids
                ):
                    injected_count += 1
                    injected_unique_ids.add(int(m.id))

        # Project URL exact injection (after title injection, before share URL)
        project_injections: List[SearchService.ConversationSearchItem] = []
        if project_conversation_ids:
            for conv_id in project_conversation_ids:
                conv = self._db.get_conversation_by_id(conversation_id=conv_id)
                if not conv:
                    continue
                project_injections.append(
                    SearchService.ConversationSearchItem(
                        content_type="conversation",
                        conversation_id=conv_id,
                        content_snippet=f"Exact project URL match: {conv.title}",
                        score=1.0,
                        created_at=conv.created_at.isoformat(),
                        conversation_title=conv.title,
                        created_by_user_name=conv.user_name,
                        created_by_user_email=conv.user_email,
                    )
                )
                if conv_id not in present_conversation_ids and conv_id not in injected_unique_ids:
                    injected_count += 1
                    injected_unique_ids.add(conv_id)

        # URL exact injection (after project URL injection)
        url_injections: List[SearchService.ConversationSearchItem] = []
        if exact_conversation_ids:
            for conv_id in exact_conversation_ids:
                conv = self._db.get_conversation_by_id(conversation_id=conv_id)
                if not conv:
                    continue
                url_injections.append(
                    SearchService.ConversationSearchItem(
                        content_type="imported_chat",
                        conversation_id=conv_id,
                        content_snippet=f"Exact URL match: {conv.title}",
                        score=1.0,
                        created_at=conv.created_at.isoformat(),
                        conversation_title=conv.title,
                        created_by_user_name=conv.user_name,
                        created_by_user_email=conv.user_email,
                    )
                )
                if conv_id not in present_conversation_ids and conv_id not in injected_unique_ids:
                    injected_count += 1
                    injected_unique_ids.add(conv_id)

        # Final items ordering: title injections, project URL injections, share URL injections, then vector-grouped items
        items = title_injections + project_injections + url_injections + base_items

        total_conversations = (
            grouped_rows[0].total_conversations if grouped_rows else 0
        ) + injected_count
        has_more = total_conversations > offset + limit

        return SearchService.ConversationSearchResult(
            items=items, total_conversations=total_conversations, has_more=has_more
        )

    def _truncate_snippet(self, snippet: str, query: str, max_length: int) -> str:
        """Truncate a snippet to a maximum length, centered around the first query term.

        Ensures the returned snippet contains the query (case-insensitive) when present.
        Adds leading/trailing ellipses when content is omitted.
        """
        text = snippet or ""
        if len(text) <= max_length:
            return text

        # Extract alphanumeric query tokens, prefer tokens length >= 3
        tokens = [t for t in re.findall(r"[A-Za-z0-9]+", query) if len(t) >= 3]
        if not tokens:
            # Fallback: simple head truncation
            return text[: max_length - 1].rstrip() + "…"

        # Find earliest match among tokens
        match_index = -1
        for token in tokens:
            m = re.search(re.escape(token), text, re.IGNORECASE)
            if m:
                match_index = m.start()
                break

        if match_index == -1:
            # No token found; head truncation
            return text[: max_length - 1].rstrip() + "…"

        half = max_length // 2
        start = max(0, match_index - half)
        end = start + max_length
        if end > len(text):
            end = len(text)
            start = max(0, end - max_length)

        fragment = text[start:end]
        prefix = "… " if start > 0 else ""
        suffix = " …" if end < len(text) else ""
        return f"{prefix}{fragment.strip()}{suffix}"

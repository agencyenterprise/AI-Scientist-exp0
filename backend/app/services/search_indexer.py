"""
Search indexer service.

Provides synchronous indexing for imported chat, draft chat messages, and active project drafts.
"""

from typing import List

from app.services.chunking_service import ChunkingService
from app.services.database import get_database
from app.services.embeddings_service import EmbeddingsService


class SearchIndexer:
    """Synchronous indexer for RAG search."""

    def __init__(
        self, embeddings_service: EmbeddingsService, chunking_service: ChunkingService
    ) -> None:
        """Initialize with dependencies."""
        self.embeddings_service = embeddings_service
        self.chunking_service = chunking_service
        self.db = get_database()

    def index_imported_chat(self, conversation_id: int) -> None:
        """Delete and re-index imported chat for a conversation."""
        conversation = self.db.get_conversation_by_id(conversation_id)
        if not conversation or not conversation.imported_chat:
            return

        messages: List[str] = [m.content for m in conversation.imported_chat]

        # Build chunks per message
        chunk_texts: List[str] = []
        chunk_meta: List[tuple[int, int]] = []  # (message_index, chunk_index)
        for message_index, text in enumerate(messages):
            chunks = self.chunking_service.chunk_text(text=text, target_chars=2500)
            for chunk_index, chunk in enumerate(chunks):
                chunk_texts.append(chunk)
                chunk_meta.append((message_index, chunk_index))

        embeddings = self.embeddings_service.embed_texts(texts=chunk_texts)

        # Write using DB mixin
        self.db.delete_imported_chat_chunks(conversation_id)
        for (message_index, chunk_index), text, vector in zip(chunk_meta, chunk_texts, embeddings):
            self.db.insert_imported_chat_chunk(
                conversation_id=conversation_id,
                message_index=message_index,
                chunk_index=chunk_index,
                text=text,
                embedding=vector,
            )

    def index_chat_message(self, chat_message_id: int) -> None:
        """Index or re-index a single chat message."""
        # Load authoritative data
        # Find message and owning draft
        messages = self.db.get_chat_messages_for_ids([chat_message_id])
        if not messages:
            return
        m = messages[0]
        message_id, project_draft_id, content, sequence_number = (
            m.id,
            m.project_draft_id,
            m.content,
            m.sequence_number,
        )

        # Get active version id for this draft (index active draft scope only)
        project_draft = self.db.get_project_draft_by_id(project_draft_id)
        if not project_draft:
            return
        active_version_id = project_draft.version_id
        conversation_id = project_draft.conversation_id

        chunks = self.chunking_service.chunk_text(text=content, target_chars=2500)
        embeddings = self.embeddings_service.embed_texts(texts=chunks)

        self.db.delete_draft_chat_chunks_by_message(message_id)
        for chunk_index, (text, vector) in enumerate(zip(chunks, embeddings)):
            self.db.insert_draft_chat_chunk(
                conversation_id=conversation_id,
                project_draft_id=project_draft_id,
                project_draft_version_id=active_version_id,
                chat_message_id=message_id,
                sequence_number=sequence_number,
                chunk_index=chunk_index,
                text=text,
                embedding=vector,
            )

    def index_active_project_draft(self, project_draft_id: int) -> None:
        """Delete and re-index the active project draft version (title + description)."""
        data = self.db.get_project_draft_by_id(project_draft_id)
        if not data:
            return
        active_version_id = data.version_id
        title, description = data.title, data.description
        conversation_id = data.conversation_id

        combined = (title or "") + "\n\n" + (description or "")
        chunks = self.chunking_service.chunk_text(text=combined, target_chars=3500)
        embeddings = self.embeddings_service.embed_texts(texts=chunks)

        self.db.delete_project_draft_chunks(project_draft_id)
        for chunk_index, (text, vector) in enumerate(zip(chunks, embeddings)):
            self.db.insert_project_draft_chunk(
                conversation_id=conversation_id,
                project_draft_id=project_draft_id,
                project_draft_version_id=active_version_id,
                chunk_index=chunk_index,
                text=text,
                embedding=vector,
            )

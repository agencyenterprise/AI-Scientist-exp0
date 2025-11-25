"""
Embeddings service.

Provides a minimal interface to compute text embeddings for search.
"""

import os
from typing import List

from openai import OpenAI


class EmbeddingsService:
    """Service for computing text embeddings using provider-specific APIs."""

    EMBEDDING_MODEL = "text-embedding-3-small"

    def __init__(self) -> None:
        """Initialize the embeddings service with OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required for embeddings")
        self._openai_client = OpenAI(api_key=api_key)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Return embeddings for the given texts.

        Args:
            texts: List of input texts
        """
        if not texts:
            return []

        # OpenAI Embeddings API expects strings and returns a list of vectors
        response = self._openai_client.embeddings.create(model=self.EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in response.data]

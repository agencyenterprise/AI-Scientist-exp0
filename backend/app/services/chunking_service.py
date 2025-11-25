"""
Chunking service.

Provides simple, deterministic text chunking utilities for indexing.
"""

from typing import List


class ChunkingService:
    """Service for splitting text into reasonably sized chunks."""

    def __init__(self) -> None:
        """Initialize the chunking service."""
        pass

    def chunk_text(self, text: str, target_chars: int) -> List[str]:
        """Split text into chunks up to target_chars using sentence boundaries when possible."""
        if not text:
            return []

        # Very lightweight sentence splitting to avoid pulling heavy libs
        # 1) Split on double newlines first (paragraphs)
        parts: List[str] = []
        for paragraph in text.split("\n\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if len(paragraph) <= target_chars:
                parts.append(paragraph)
                continue

            # 2) Fallback: split on sentences
            sentences = []
            start = 0
            for i, ch in enumerate(paragraph):
                if ch in ".!?" and (i + 1 == len(paragraph) or paragraph[i + 1] == " "):
                    sentences.append(paragraph[start : i + 1])
                    start = i + 1
            if start < len(paragraph):
                sentences.append(paragraph[start:])

            current = ""
            for sentence in sentences:
                candidate = (current + " " + sentence).strip() if current else sentence.strip()
                if len(candidate) <= target_chars:
                    current = candidate
                else:
                    if current:
                        parts.append(current)
                    # sentence might still be longer than target; hard split
                    while len(sentence) > target_chars:
                        parts.append(sentence[:target_chars])
                        sentence = sentence[target_chars:]
                    current = sentence
            if current:
                parts.append(current)

        return parts

"""Chunker interface for text segmentation."""

from typing import Protocol


class IChunker(Protocol):
    """Protocol for text chunking services."""

    def chunk(self, text: str) -> list[str]:
        """Split text into chunks.

        Args:
            text: Input text to chunk.

        Returns:
            List of text chunks.

        Raises:
            IngestionError: If chunking fails.
        """
        ...

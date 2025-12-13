"""Embedder interface for text embedding."""

from typing import Protocol


class IEmbedder(Protocol):
    """Protocol for text embedding services."""

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a batch.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.

        Raises:
            EmbeddingError: If embedding fails.
        """
        ...

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query with instruction prefix.

        Args:
            query: Query text to embed.

        Returns:
            Embedding vector.

        Raises:
            EmbeddingError: If embedding fails.
        """
        ...

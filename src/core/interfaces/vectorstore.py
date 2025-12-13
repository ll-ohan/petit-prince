"""Vector store interface for storage and retrieval."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class SearchResult:
    """Vector search result."""

    text: str
    score: float
    metadata: dict


class IVectorStore(Protocol):
    """Protocol for vector database operations."""

    async def create_collection(self, dimension: int) -> None:
        """Create or recreate collection.

        Args:
            dimension: Embedding vector dimension.

        Raises:
            VectorStoreError: If creation fails.
        """
        ...

    async def upsert(self, texts: list[str], vectors: list[list[float]]) -> None:
        """Insert or update vectors with their texts.

        Args:
            texts: List of text chunks.
            vectors: Corresponding embedding vectors.

        Raises:
            VectorStoreError: If upsert fails.
        """
        ...

    async def search(self, query_vector: list[float], top_k: int) -> list[SearchResult]:
        """Search for similar vectors.

        Args:
            query_vector: Query embedding vector.
            top_k: Number of results to return.

        Returns:
            List of search results ordered by similarity.

        Raises:
            VectorStoreError: If search fails.
        """
        ...

    async def collection_exists(self) -> bool:
        """Check if collection exists.

        Returns:
            True if collection exists, False otherwise.
        """
        ...

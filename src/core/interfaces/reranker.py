"""Reranker interface for document reranking."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class RankedDocument:
    """Document with reranking score."""

    text: str
    score: float
    original_rank: int


class IReranker(Protocol):
    """Protocol for document reranking services."""

    async def rerank(
        self, query: str, documents: list[str], top_n: int
    ) -> list[RankedDocument]:
        """Rerank documents by relevance to query.

        Args:
            query: User query.
            documents: List of document texts to rerank.
            top_n: Number of top documents to return.

        Returns:
            List of reranked documents with scores.

        Raises:
            RerankError: If reranking fails.
        """
        ...

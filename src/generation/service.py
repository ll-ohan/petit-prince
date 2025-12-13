"""Generation service orchestrating RAG flow."""

import logging
import time

from src.core.exceptions import GenerationError, RetrievalError, RerankError
from src.core.interfaces.embedder import IEmbedder
from src.core.interfaces.generator import IGenerator
from src.core.interfaces.reranker import IReranker
from src.core.interfaces.vectorstore import IVectorStore
from src.generation.prompt_builder import PromptBuilder
from src.generation.response_handler import RequestMetrics

logger = logging.getLogger(__name__)


class GenerationService:
    """Orchestrates RAG flow: retrieve, rerank, generate."""

    def __init__(
        self,
        embedder: IEmbedder,
        vectorstore: IVectorStore,
        reranker: IReranker,
        generator: IGenerator,
        top_k: int,
        top_x: int,
        threshold: float,
    ):
        """Initialize generation service.

        Args:
            embedder: Embedding service.
            vectorstore: Vector store.
            reranker: Reranking service.
            generator: Generation service.
            top_k: Initial retrieval count.
            top_x: Post-rerank count.
            threshold: Relevance threshold.
        """
        self.embedder = embedder
        self.vectorstore = vectorstore
        self.reranker = reranker
        self.generator = generator
        self.top_k = top_k
        self.top_x = top_x
        self.threshold = threshold

        self.prompt_builder = PromptBuilder()

    async def process_query(
        self, messages: list[dict], metrics: RequestMetrics
    ) -> tuple[list[dict], list]:
        """Process query through RAG pipeline.

        Args:
            messages: Conversation messages.
            metrics: Metrics tracker.

        Returns:
            Tuple of (final_messages, reranked_documents).

        Raises:
            RetrievalError: If retrieval fails.
            RerankError: If reranking fails.
        """
        # Extract last user message as query
        query = messages[-1]["content"]

        # 1. Embed query
        start = time.perf_counter()
        query_vector = await self.embedder.embed_query(query)
        metrics.embedding_ms = (time.perf_counter() - start) * 1000

        # 2. Vector search
        start = time.perf_counter()
        search_results = await self.vectorstore.search(query_vector, self.top_k)
        metrics.search_ms = (time.perf_counter() - start) * 1000
        metrics.documents_retrieved = len(search_results)

        logger.info("Retrieved %d documents from vector search", len(search_results))

        if not search_results:
            logger.warning("No documents found in vector search")
            return messages, []

        # 3. Rerank
        start = time.perf_counter()
        try:
            documents_to_rerank = [r.text for r in search_results]
            reranked = await self.reranker.rerank(query, documents_to_rerank, self.top_x)
        except RerankError as e:
            # Fallback to vector search ranking
            logger.warning("Reranker failed, falling back to vector similarity: %s", e)
            from src.core.interfaces.reranker import RankedDocument

            reranked = [
                RankedDocument(text=r.text, score=r.score, original_rank=i)
                for i, r in enumerate(search_results[: self.top_x])
            ]

        metrics.rerank_ms = (time.perf_counter() - start) * 1000
        metrics.documents_after_rerank = len(reranked)
        metrics.relevance_scores = [d.score for d in reranked]
        metrics.documents_above_threshold = sum(1 for d in reranked if d.score >= self.threshold)
        metrics.threshold_used = self.threshold

        logger.info(
            "Reranked to %d documents (%d above threshold %.2f)",
            len(reranked),
            metrics.documents_above_threshold,
            self.threshold,
        )

        # 4. Build prompt with context
        final_messages = self.prompt_builder.build(messages, reranked, self.threshold)

        # 5. Count tokens for metrics
        prompt_text = "\n".join(m["content"] for m in final_messages)
        try:
            metrics.prompt_tokens = await self.generator.count_tokens(prompt_text)
        except GenerationError:
            logger.warning("Token counting failed, using estimate")
            metrics.prompt_tokens = len(prompt_text) // 4

        return final_messages, reranked

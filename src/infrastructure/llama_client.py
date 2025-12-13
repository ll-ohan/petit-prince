"""Llama.cpp client for embeddings, reranking, and generation."""

import asyncio
import logging
import math
from typing import AsyncIterator

import httpx

from src.config.settings import LlamaConfig
from src.core.exceptions import EmbeddingError, GenerationError, RerankError
from src.core.interfaces.reranker import RankedDocument

logger = logging.getLogger(__name__)


class LlamaClient:
    """Client for llama.cpp server with retry logic."""

    def __init__(self, config: LlamaConfig):
        """Initialize llama.cpp client.

        Args:
            config: Llama configuration.
        """
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url, timeout=config.timeout, follow_redirects=True
        )

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts using llama.cpp.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.

        Raises:
            EmbeddingError: If embedding fails.
        """
        if not texts:
            return []

        try:
            response = await self._retry_request(
                "POST",
                "/v1/embeddings",
                json={"model": self.config.embedding_model, "input": texts, "encoding_format": "float"},
            )

            data = response.json()
            embeddings = [item["embedding"] for item in data["data"]]

            # Validate dimensions
            for idx, emb in enumerate(embeddings):
                if len(emb) != self.config.embedding_dim:
                    raise EmbeddingError(
                        f"Embedding dimension mismatch: expected {self.config.embedding_dim}, got {len(emb)}",
                        context={"batch_index": idx, "expected": self.config.embedding_dim, "actual": len(emb)},
                    )

                # Validate values
                if any(math.isnan(v) or math.isinf(v) for v in emb):
                    raise EmbeddingError(
                        "Invalid embedding values: contains NaN or Inf",
                        context={"batch_index": idx},
                    )

            logger.debug("Embedded batch of %d texts", len(texts))
            return embeddings

        except httpx.HTTPStatusError as e:
            raise EmbeddingError(
                f"Embedding batch failed: llama.cpp returned status {e.response.status_code}",
                context={
                    "batch_size": len(texts),
                    "model": self.config.embedding_model,
                    "endpoint": "/v1/embeddings",
                    "response_body": e.response.text[:500],
                },
            ) from e
        except httpx.RequestError as e:
            raise EmbeddingError(
                f"Embedding batch failed: {type(e).__name__}",
                context={
                    "batch_size": len(texts),
                    "endpoint": f"{self.config.base_url}/v1/embeddings",
                },
            ) from e

    async def embed_query(self, query: str) -> list[float]:
        """Embed query with instruction prefix.

        Args:
            query: Query text.

        Returns:
            Embedding vector.

        Raises:
            EmbeddingError: If embedding fails.
        """
        # Add instruction for better retrieval
        instructed_query = f"Instruct: Given a query, retrieve relevant passages\nQuery: {query}"
        embeddings = await self.embed_batch([instructed_query])
        return embeddings[0]

    async def rerank(self, query: str, documents: list[str], top_n: int) -> list[RankedDocument]:
        """Rerank documents by relevance.

        Args:
            query: Query text.
            documents: List of document texts.
            top_n: Number of top documents to return.

        Returns:
            List of reranked documents with scores.

        Raises:
            RerankError: If reranking fails.
        """
        if not documents:
            return []

        try:
            response = await self._retry_request(
                "POST",
                "/v1/rerank",
                json={
                    "model": self.config.reranker_model,
                    "query": query,
                    "documents": documents,
                    "top_n": top_n,
                },
            )

            data = response.json()
            results = data.get("results", [])

            ranked = []
            for item in results:
                ranked.append(
                    RankedDocument(
                        text=documents[item["index"]],
                        score=item["relevance_score"],
                        original_rank=item["index"],
                    )
                )

            logger.debug("Reranked %d documents, returned top %d", len(documents), len(ranked))
            return ranked

        except httpx.HTTPStatusError as e:
            raise RerankError(
                f"Reranking failed: llama.cpp returned status {e.response.status_code}",
                context={
                    "query": query[:100],
                    "document_count": len(documents),
                    "response_body": e.response.text[:500],
                },
            ) from e
        except httpx.RequestError as e:
            raise RerankError(
                f"Reranking failed: {type(e).__name__}",
                context={"endpoint": f"{self.config.base_url}/v1/rerank"},
            ) from e

    async def generate(self, messages: list[dict]) -> str:
        """Generate response (blocking).

        Args:
            messages: List of message dicts.

        Returns:
            Generated text.

        Raises:
            GenerationError: If generation fails.
        """
        try:
            response = await self._retry_request(
                "POST",
                "/v1/chat/completions",
                json={
                    "model": self.config.generation_model,
                    "messages": messages,
                    "stream": False,
                },
            )

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            logger.debug("Generated %d characters", len(content))
            return content

        except httpx.HTTPStatusError as e:
            raise GenerationError(
                f"Generation failed: llama.cpp returned status {e.response.status_code}",
                context={"response_body": e.response.text[:500]},
            ) from e
        except httpx.RequestError as e:
            raise GenerationError(
                f"Generation failed: {type(e).__name__}",
                context={"endpoint": f"{self.config.base_url}/v1/chat/completions"},
            ) from e

    async def generate_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Generate response (streaming).

        Args:
            messages: List of message dicts.

        Yields:
            Text chunks.

        Raises:
            GenerationError: If generation fails.
        """
        try:
            async with self.client.stream(
                "POST",
                "/v1/chat/completions",
                json={
                    "model": self.config.generation_model,
                    "messages": messages,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break

                        import json

                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]

        except httpx.HTTPStatusError as e:
            raise GenerationError(
                f"Streaming generation failed: status {e.response.status_code}",
                context={"response_body": str(e.response.text)[:500]},
            ) from e
        except httpx.RequestError as e:
            raise GenerationError(
                f"Streaming generation failed: {type(e).__name__}",
            ) from e

    async def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to tokenize.

        Returns:
            Token count.

        Raises:
            GenerationError: If tokenization fails.
        """
        try:
            response = await self._retry_request(
                "POST", "/tokenize", json={"content": text}
            )

            data = response.json()
            return len(data["tokens"])

        except httpx.HTTPStatusError as e:
            raise GenerationError(
                f"Tokenization failed: status {e.response.status_code}",
                context={"text_length": len(text)},
            ) from e
        except httpx.RequestError as e:
            raise GenerationError(f"Tokenization failed: {type(e).__name__}") from e

    async def _retry_request(
        self, method: str, url: str, max_attempts: int = 3, **kwargs
    ) -> httpx.Response:
        """Execute HTTP request with retry logic.

        Args:
            method: HTTP method.
            url: URL path.
            max_attempts: Maximum retry attempts.
            **kwargs: Additional arguments for request.

        Returns:
            HTTP response.

        Raises:
            httpx.HTTPStatusError: If request fails after retries.
            httpx.RequestError: If network error persists.
        """
        last_exception = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                if attempt < max_attempts:
                    delay = min(2 ** (attempt - 1), 30)
                    logger.warning(
                        "Retry %d/%d for %s %s: %s. Waiting %.1fs",
                        attempt,
                        max_attempts,
                        method,
                        url,
                        str(e),
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise

            except httpx.HTTPStatusError as e:
                # Retry on 5xx errors
                if e.response.status_code >= 500 and attempt < max_attempts:
                    delay = min(2 ** (attempt - 1), 30)
                    logger.warning(
                        "Retry %d/%d for %s %s: status %d. Waiting %.1fs",
                        attempt,
                        max_attempts,
                        method,
                        url,
                        e.response.status_code,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise

        raise last_exception

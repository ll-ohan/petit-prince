"""Response handler for OpenAI-compatible formats."""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Metrics for request processing."""

    start_time: float = field(default_factory=time.perf_counter)
    embedding_ms: float = 0
    search_ms: float = 0
    rerank_ms: float = 0
    generation_ms: float = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    documents_retrieved: int = 0
    documents_after_rerank: int = 0
    relevance_scores: list[float] = field(default_factory=list)
    documents_above_threshold: int = 0
    threshold_used: float = 0.0

    @property
    def total_ms(self) -> float:
        """Total elapsed time in milliseconds."""
        return (time.perf_counter() - self.start_time) * 1000

    @property
    def total_tokens(self) -> int:
        """Total token count."""
        return self.prompt_tokens + self.completion_tokens

    def to_openai_usage(self) -> dict:
        """Return strictly OpenAI-compliant usage object."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }

    def to_extended_metrics(self) -> dict:
        """Return extended metrics (non-OpenAI)."""
        return {
            "timings": {
                "embedding_ms": round(self.embedding_ms, 2),
                "search_ms": round(self.search_ms, 2),
                "rerank_ms": round(self.rerank_ms, 2),
                "generation_ms": round(self.generation_ms, 2),
                "total_ms": round(self.total_ms, 2),
            },
            "retrieval": {
                "documents_retrieved": self.documents_retrieved,
                "documents_after_rerank": self.documents_after_rerank,
                "relevance_scores": [round(s, 3) for s in self.relevance_scores],
                "documents_above_threshold": self.documents_above_threshold,
                "threshold_used": self.threshold_used,
            },
        }


class ResponseHandler:
    """Handle OpenAI-compatible response formatting."""

    MODEL_NAME = "petit-prince-rag"

    def format_completion(
        self, content: str, metrics: RequestMetrics, include_extended: bool = False
    ) -> dict:
        """Format blocking completion response.

        Args:
            content: Generated content.
            metrics: Request metrics.
            include_extended: Include extended metrics.

        Returns:
            OpenAI-compatible completion response.
        """
        response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": self.MODEL_NAME,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": metrics.to_openai_usage(),
        }

        if include_extended:
            response["x_metrics"] = metrics.to_extended_metrics()

        return response

    async def format_streaming_completion(
        self,
        content_stream: AsyncIterator[str],
        metrics: RequestMetrics,
        include_extended: bool = False,
    ) -> AsyncIterator[str]:
        """Format streaming completion response.

        Args:
            content_stream: Stream of content chunks.
            metrics: Request metrics.
            include_extended: Include extended metrics.

        Yields:
            SSE-formatted data chunks.
        """
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        created = int(time.time())

        # First chunk with role
        yield self._format_sse_chunk(
            {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": self.MODEL_NAME,
                "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
            }
        )

        # Content chunks
        async for chunk in content_stream:
            yield self._format_sse_chunk(
                {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": self.MODEL_NAME,
                    "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}],
                }
            )

        # Final chunk with usage
        final_chunk = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": self.MODEL_NAME,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": metrics.to_openai_usage(),
        }

        if include_extended:
            final_chunk["x_metrics"] = metrics.to_extended_metrics()

        yield self._format_sse_chunk(final_chunk)

        # Done marker
        yield "data: [DONE]\n\n"

    def _format_sse_chunk(self, data: dict) -> str:
        """Format data as SSE chunk.

        Args:
            data: Data to format.

        Returns:
            SSE-formatted string.
        """
        return f"data: {json.dumps(data)}\n\n"

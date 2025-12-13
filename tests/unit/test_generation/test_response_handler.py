"""Tests for ResponseHandler."""

import pytest

from src.generation.response_handler import RequestMetrics, ResponseHandler


class TestResponseHandler:
    """Test response formatting."""

    def test_format_completion_basic(self):
        """Basic blocking completion format."""
        handler = ResponseHandler()
        metrics = RequestMetrics()
        metrics.prompt_tokens = 100
        metrics.completion_tokens = 50

        response = handler.format_completion("Generated text", metrics, include_extended=False)

        assert response["object"] == "chat.completion"
        assert response["model"] == "petit-prince-rag"
        assert response["choices"][0]["message"]["content"] == "Generated text"
        assert response["choices"][0]["finish_reason"] == "stop"
        assert response["usage"]["prompt_tokens"] == 100
        assert response["usage"]["completion_tokens"] == 50
        assert response["usage"]["total_tokens"] == 150
        assert "x_metrics" not in response

    def test_format_completion_with_extended_metrics(self):
        """Completion with extended metrics includes x_metrics."""
        handler = ResponseHandler()
        metrics = RequestMetrics()
        metrics.prompt_tokens = 100
        metrics.completion_tokens = 50
        metrics.embedding_ms = 45.0
        metrics.search_ms = 12.0
        metrics.rerank_ms = 89.0
        metrics.generation_ms = 2340.0
        metrics.documents_retrieved = 20
        metrics.documents_after_rerank = 5
        metrics.relevance_scores = [0.92, 0.87, 0.76, 0.71, 0.68]
        metrics.documents_above_threshold = 3
        metrics.threshold_used = 0.7

        response = handler.format_completion("Generated text", metrics, include_extended=True)

        assert "x_metrics" in response
        assert response["x_metrics"]["timings"]["embedding_ms"] == 45.0
        assert response["x_metrics"]["timings"]["search_ms"] == 12.0
        assert response["x_metrics"]["timings"]["rerank_ms"] == 89.0
        assert response["x_metrics"]["timings"]["generation_ms"] == 2340.0
        assert response["x_metrics"]["retrieval"]["documents_retrieved"] == 20
        assert response["x_metrics"]["retrieval"]["documents_after_rerank"] == 5
        assert len(response["x_metrics"]["retrieval"]["relevance_scores"]) == 5
        assert response["x_metrics"]["retrieval"]["documents_above_threshold"] == 3
        assert response["x_metrics"]["retrieval"]["threshold_used"] == 0.7

    def test_openai_usage_format(self):
        """Usage object is strictly OpenAI-compliant."""
        handler = ResponseHandler()
        metrics = RequestMetrics()
        metrics.prompt_tokens = 1847
        metrics.completion_tokens = 234

        response = handler.format_completion("Text", metrics)

        usage = response["usage"]
        assert set(usage.keys()) == {"prompt_tokens", "completion_tokens", "total_tokens"}
        assert usage["prompt_tokens"] == 1847
        assert usage["completion_tokens"] == 234
        assert usage["total_tokens"] == 2081

    async def test_streaming_format(self):
        """Streaming response follows SSE format."""
        handler = ResponseHandler()
        metrics = RequestMetrics()
        metrics.prompt_tokens = 100
        metrics.completion_tokens = 20

        async def mock_stream():
            yield "Le "
            yield "renard"

        chunks = []
        async for chunk in handler.format_streaming_completion(
            mock_stream(), metrics, include_extended=False
        ):
            chunks.append(chunk)

        # First chunk has role
        assert 'data: {' in chunks[0]
        assert '"role"' in chunks[0] and '"assistant"' in chunks[0]

        # Content chunks
        assert '"content"' in chunks[1] and '"Le "' in chunks[1]
        assert '"content"' in chunks[2] and '"renard"' in chunks[2]

        # Final chunk has usage
        assert '"finish_reason"' in chunks[3] and '"stop"' in chunks[3]
        assert '"usage"' in chunks[3]

        # Done marker
        assert chunks[-1] == "data: [DONE]\n\n"

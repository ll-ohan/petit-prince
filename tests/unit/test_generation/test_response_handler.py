"""Unit tests for ResponseHandler."""

import pytest

from src.generation.response_handler import RequestMetrics, ResponseHandler


@pytest.mark.unit
class TestResponseHandler:

    def test_format_blocking_response(self):
        """Test OpenAI-compatible blocking response format."""
        handler = ResponseHandler()
        metrics = RequestMetrics(prompt_tokens=10, completion_tokens=5)

        response = handler.format_completion("Hello", metrics)

        assert response["object"] == "chat.completion"
        assert response["choices"][0]["message"]["content"] == "Hello"
        assert response["usage"]["total_tokens"] == 15

    def test_format_usage_calculation(self):
        """Test correctness of total tokens calculation."""
        metrics = RequestMetrics(prompt_tokens=100, completion_tokens=50)
        assert metrics.total_tokens == 150

        openai_usage = metrics.to_openai_usage()
        assert openai_usage["total_tokens"] == 150

    def test_format_extended_metrics(self):
        """Test inclusion of x_metrics."""
        handler = ResponseHandler()
        metrics = RequestMetrics()
        metrics.embedding_ms = 100

        response = handler.format_completion("Hi", metrics, include_extended=True)

        assert "x_metrics" in response
        assert response["x_metrics"]["timings"]["embedding_ms"] == 100

    @pytest.mark.asyncio
    async def test_format_streaming_chunks(self):
        """Test SSE formatting for streaming."""
        handler = ResponseHandler()
        metrics = RequestMetrics()

        async def mock_stream():
            yield "He"
            yield "llo"

        chunks = []
        async for chunk in handler.format_streaming_completion(mock_stream(), metrics):
            chunks.append(chunk)

        assert len(chunks) >= 3
        assert 'data: {"id":' in chunks[0]
        assert "data: [DONE]" in chunks[-1]

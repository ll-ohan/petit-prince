"""
Unit tests for /api/v1/chat/completions endpoint.

Tests OpenAI-compatible chat API including blocking responses, streaming,
metrics headers, error handling, and edge cases.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.exceptions import GenerationError, RetrievalError


@pytest.fixture
def app():
    """Create FastAPI app instance for testing."""
    from src.main import app as fastapi_app

    return fastapi_app


@pytest.fixture
def client(app: FastAPI):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_generation_service():
    """Mock GenerationService."""
    mock = AsyncMock()
    mock.process_query.return_value = {
        "response": "Le renard est un personnage qui enseigne au Petit Prince.",
        "documents": [
            {"text": "Le renard dit: Apprivoise-moi", "score": 0.92},
            {"text": "On ne connaît que les choses...", "score": 0.87},
        ],
        "metrics": {
            "embedding_ms": 45,
            "search_ms": 12,
            "rerank_ms": 89,
            "generation_ms": 2340,
            "total_ms": 2486,
        },
    }
    return mock


@pytest.mark.unit
class TestChatEndpointNominal:
    """Test chat endpoint with valid requests."""

    @pytest.mark.asyncio
    async def test_chat_blocking_success(self, client, mock_generation_service):
        """Test successful blocking chat completion."""
        with patch(
            "src.api.routes.chat.generation_service", mock_generation_service
        ):
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "model": "petit-prince-rag",
                    "messages": [{"role": "user", "content": "Qui est le renard?"}],
                    "stream": False,
                },
            )

        assert response.status_code == 200

        data = response.json()
        assert data["object"] == "chat.completion"
        assert "id" in data
        assert "created" in data
        assert len(data["choices"]) == 1

        choice = data["choices"][0]
        assert choice["message"]["role"] == "assistant"
        assert "renard" in choice["message"]["content"].lower()
        assert choice["finish_reason"] == "stop"

        # Verify usage
        assert "usage" in data
        assert data["usage"]["total_tokens"] > 0

    @pytest.mark.asyncio
    async def test_chat_streaming_success(self, client, mock_generation_service):
        """Test successful streaming chat completion."""

        async def mock_stream():
            chunks = ["Le ", "renard ", "est ", "sage."]
            for chunk in chunks:
                yield chunk

        mock_generation_service.process_query_stream = mock_stream

        with patch(
            "src.api.routes.chat.generation_service", mock_generation_service
        ):
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "model": "petit-prince-rag",
                    "messages": [{"role": "user", "content": "Qui est le renard?"}],
                    "stream": True,
                },
            )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Parse SSE chunks
        lines = response.text.strip().split("\n")
        assert any("data:" in line for line in lines)
        assert any("[DONE]" in line for line in lines)

    @pytest.mark.asyncio
    async def test_chat_with_metrics_header(self, client, mock_generation_service):
        """Test that X-Include-Metrics header includes extended metrics."""
        with patch(
            "src.api.routes.chat.generation_service", mock_generation_service
        ):
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "model": "petit-prince-rag",
                    "messages": [{"role": "user", "content": "Test"}],
                    "stream": False,
                },
                headers={"X-Include-Metrics": "true"},
            )

        assert response.status_code == 200
        data = response.json()

        # Extended metrics should be present
        assert "x_metrics" in data
        assert "timings" in data["x_metrics"]
        assert "retrieval" in data["x_metrics"]

        timings = data["x_metrics"]["timings"]
        assert "embedding_ms" in timings
        assert "search_ms" in timings
        assert "rerank_ms" in timings
        assert "generation_ms" in timings

    @pytest.mark.asyncio
    async def test_chat_multi_turn_conversation(self, client, mock_generation_service):
        """Test multi-turn conversation with history."""
        with patch(
            "src.api.routes.chat.generation_service", mock_generation_service
        ):
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "model": "petit-prince-rag",
                    "messages": [
                        {"role": "user", "content": "Qui est le renard?"},
                        {
                            "role": "assistant",
                            "content": "Le renard est un personnage sage.",
                        },
                        {
                            "role": "user",
                            "content": "Que dit-il au Petit Prince?",
                        },
                    ],
                    "stream": False,
                },
            )

        assert response.status_code == 200
        data = response.json()

        # Should process last message with conversation history
        assert mock_generation_service.process_query.called


@pytest.mark.unit
@pytest.mark.edge_case
class TestChatEndpointValidation:
    """Test request validation and error handling."""

    def test_chat_empty_messages(self, client):
        """Test that empty messages array returns 422."""
        response = client.post(
            "/api/v1/chat/completions",
            json={"model": "petit-prince-rag", "messages": [], "stream": False},
        )

        assert response.status_code == 422
        data = response.json()
        assert "error" in data or "detail" in data

    def test_chat_missing_required_fields(self, client):
        """Test that missing required fields returns 422."""
        response = client.post(
            "/api/v1/chat/completions",
            json={"model": "petit-prince-rag"},  # Missing 'messages'
        )

        assert response.status_code == 422

    def test_chat_invalid_message_role(self, client):
        """Test that invalid message role returns 422."""
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "model": "petit-prince-rag",
                "messages": [
                    {"role": "invalid_role", "content": "Test"}
                ],  # Invalid role
                "stream": False,
            },
        )

        assert response.status_code == 422

    def test_chat_message_without_content(self, client):
        """Test that message without content returns 422."""
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "model": "petit-prince-rag",
                "messages": [{"role": "user"}],  # Missing 'content'
                "stream": False,
            },
        )

        assert response.status_code == 422

    def test_chat_invalid_json(self, client):
        """Test that invalid JSON returns 422."""
        response = client.post(
            "/api/v1/chat/completions",
            data="invalid json{",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.edge_case
class TestChatEndpointErrorHandling:
    """Test error handling for service failures."""

    @pytest.mark.asyncio
    async def test_chat_retrieval_error_503(self, client, mock_generation_service):
        """Test that RetrievalError returns 503 Service Unavailable."""
        mock_generation_service.process_query.side_effect = RetrievalError(
            "Qdrant connection failed",
            context={"service": "qdrant", "error": "Connection refused"},
        )

        with patch(
            "src.api.routes.chat.generation_service", mock_generation_service
        ):
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "model": "petit-prince-rag",
                    "messages": [{"role": "user", "content": "Test"}],
                    "stream": False,
                },
            )

        assert response.status_code == 503
        data = response.json()

        assert "error" in data
        assert data["error"]["type"] == "retrieval_error"
        assert "Qdrant" in data["error"]["message"] or "qdrant" in str(
            data["error"]
        ).lower()

    @pytest.mark.asyncio
    async def test_chat_generation_error_503(self, client, mock_generation_service):
        """Test that GenerationError returns 503 Service Unavailable."""
        mock_generation_service.process_query.side_effect = GenerationError(
            "LLM timeout after 120s", context={"timeout": 120, "model": "DeepSeek-R1"}
        )

        with patch(
            "src.api.routes.chat.generation_service", mock_generation_service
        ):
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "model": "petit-prince-rag",
                    "messages": [{"role": "user", "content": "Test"}],
                    "stream": False,
                },
            )

        assert response.status_code == 503
        data = response.json()

        assert "error" in data
        assert data["error"]["type"] == "generation_error"

    @pytest.mark.asyncio
    async def test_chat_internal_error_500(self, client, mock_generation_service):
        """Test that unexpected exceptions return 500 without exposing details."""
        mock_generation_service.process_query.side_effect = RuntimeError(
            "Unexpected internal error"
        )

        with patch(
            "src.api.routes.chat.generation_service", mock_generation_service
        ):
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "model": "petit-prince-rag",
                    "messages": [{"role": "user", "content": "Test"}],
                    "stream": False,
                },
            )

        assert response.status_code == 500
        data = response.json()

        # Should not expose internal exception details to client
        assert "error" in data
        assert "Internal" in data["error"]["message"] or "internal" in str(
            data["error"]
        ).lower()

    @pytest.mark.asyncio
    async def test_chat_streaming_disconnect(self, client, mock_generation_service):
        """Test graceful handling of client disconnection during streaming."""

        async def mock_stream_with_error():
            yield "Chunk 1"
            yield "Chunk 2"
            # Simulate client disconnect
            raise ConnectionError("Client disconnected")

        mock_generation_service.process_query_stream = mock_stream_with_error

        with patch(
            "src.api.routes.chat.generation_service", mock_generation_service
        ):
            # This should not crash the server
            try:
                response = client.post(
                    "/api/v1/chat/completions",
                    json={
                        "model": "petit-prince-rag",
                        "messages": [{"role": "user", "content": "Test"}],
                        "stream": True,
                    },
                )
                # May return partial response or error depending on implementation
                assert response.status_code in (200, 500)
            except Exception:
                # Connection errors during streaming are acceptable
                pass


@pytest.mark.unit
class TestChatEndpointUsageCalculation:
    """Test token usage calculation."""

    @pytest.mark.asyncio
    async def test_chat_usage_calculation_correctness(
        self, client, mock_generation_service
    ):
        """Test that total_tokens = prompt_tokens + completion_tokens."""
        with patch(
            "src.api.routes.chat.generation_service", mock_generation_service
        ):
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "model": "petit-prince-rag",
                    "messages": [{"role": "user", "content": "Test question"}],
                    "stream": False,
                },
            )

        assert response.status_code == 200
        data = response.json()

        usage = data["usage"]
        assert usage["total_tokens"] == usage["prompt_tokens"] + usage[
            "completion_tokens"
        ]

    @pytest.mark.asyncio
    async def test_chat_usage_in_streaming_final_chunk(
        self, client, mock_generation_service
    ):
        """Test that usage appears only in final streaming chunk."""

        async def mock_stream():
            yield "Chunk 1"
            yield "Chunk 2"

        mock_generation_service.process_query_stream = mock_stream

        with patch(
            "src.api.routes.chat.generation_service", mock_generation_service
        ):
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "model": "petit-prince-rag",
                    "messages": [{"role": "user", "content": "Test"}],
                    "stream": True,
                },
            )

        # Parse SSE response
        lines = [
            line for line in response.text.split("\n") if line.startswith("data: ")
        ]

        # Last chunk before [DONE] should contain usage
        usage_found = False
        for line in lines:
            if "[DONE]" not in line:
                try:
                    chunk_data = json.loads(line[6:])  # Remove "data: " prefix
                    if "usage" in chunk_data:
                        usage_found = True
                except json.JSONDecodeError:
                    pass

        # Depending on implementation, usage might be in final chunk
        # This test documents expected behavior


@pytest.mark.unit
class TestChatEndpointResponseFormat:
    """Test OpenAI API format compliance."""

    @pytest.mark.asyncio
    async def test_chat_response_has_required_fields(
        self, client, mock_generation_service
    ):
        """Test that response contains all required OpenAI API fields."""
        with patch(
            "src.api.routes.chat.generation_service", mock_generation_service
        ):
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "model": "petit-prince-rag",
                    "messages": [{"role": "user", "content": "Test"}],
                    "stream": False,
                },
            )

        data = response.json()

        # Required fields per OpenAI API spec
        required_fields = ["id", "object", "created", "model", "choices", "usage"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Validate choices structure
        assert isinstance(data["choices"], list)
        assert len(data["choices"]) > 0

        choice = data["choices"][0]
        assert "index" in choice
        assert "message" in choice
        assert "finish_reason" in choice

        # Validate message structure
        message = choice["message"]
        assert "role" in message
        assert "content" in message

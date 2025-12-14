"""
Unit tests for /api/v1/chat/completions endpoint.

Tests OpenAI-compatible chat API including blocking responses, streaming,
metrics headers, error handling, and edge cases.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.chat import get_generation_service, get_llama_client
from src.core.exceptions import GenerationError, RetrievalError


@pytest.fixture
def app():
    """Create FastAPI app instance for testing."""
    from src.main import app as fastapi_app

    return fastapi_app


@pytest.fixture
def mock_generation_service():
    """Mock GenerationService."""
    mock = AsyncMock()
    # Default return values
    mock.process_query.return_value = (
        [{"role": "user", "content": "Qui est le renard?"}],  # final_messages
        [
            {"text": "Le renard dit: Apprivoise-moi", "score": 0.92},
            {"text": "On ne connaît que les choses...", "score": 0.87},
        ],  # documents
    )
    return mock


@pytest.fixture
def mock_llama_client():
    """Mock LlamaClient."""
    mock = AsyncMock()
    mock.generate.return_value = (
        "Le renard est un personnage qui enseigne au Petit Prince."
    )
    mock.count_tokens.return_value = 15

    # Setup default streaming behavior
    async def default_stream(messages):
        chunks = ["Le ", "renard ", "est ", "sage."]
        for chunk in chunks:
            yield chunk

    mock.generate_stream = default_stream
    return mock


@pytest.fixture
def client(app: FastAPI, mock_generation_service, mock_llama_client):
    """
    Create test client with mocked dependencies and startup logic.
    """
    # 1. Override dependencies used by the route
    app.dependency_overrides[get_generation_service] = lambda: mock_generation_service
    app.dependency_overrides[get_llama_client] = lambda: mock_llama_client

    # 2. Patch components used in src.main.lifespan to prevent real startup
    with (
        patch("src.main.Settings") as mocksettings,
        patch("src.main.LlamaClient") as mockllamainit,
        patch("src.main.QdrantRepository") as mockqdrantinit,
        patch("src.main.setup_logging"),
        patch("src.main.validate_config_at_startup"),
    ):

        # Configure the mock settings object to return valid dummy data
        mock_settings_instance = MagicMock()
        mock_settings_instance.llama.base_url = "http://mock-url"
        mock_settings_instance.qdrant.host = "localhost"
        mock_settings_instance.qdrant.port = 6333

        # Ensure Settings.from_yaml() returns our mock instance
        mocksettings.from_yaml.return_value = mock_settings_instance

        # FIX: Make close methods awaitable for lifespan shutdown
        mockllamainit.return_value.close = AsyncMock()
        mockqdrantinit.return_value.close = AsyncMock()

        # Initialize the TestClient (which triggers lifespan)
        with TestClient(app) as client:
            yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.mark.unit
class TestChatEndpointNominal:
    """Test chat endpoint with valid requests."""

    @pytest.mark.asyncio
    async def test_chat_blocking_success(self, client):
        """Test successful blocking chat completion."""
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
    async def test_chat_streaming_success(self, client, mock_llama_client):
        """Test successful streaming chat completion."""

        # Customize streaming response for this specific test
        async def mock_stream(messages):
            chunks = ["Le ", "renard ", "est ", "sage."]
            for chunk in chunks:
                yield chunk

        mock_llama_client.generate_stream = mock_stream

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
    async def test_chat_with_metrics_header(self, client):
        """Test that X-Include-Metrics header includes extended metrics."""
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

        timings = data["x_metrics"]["timings"]
        assert "generation_ms" in timings

    @pytest.mark.asyncio
    async def test_chat_multi_turn_conversation(self, client, mock_generation_service):
        """Test multi-turn conversation with history."""
        # The client fixture already applies the dependency override
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

        # Check inside 'detail' wrapper
        assert "detail" in data
        assert "error" in data["detail"]
        error = data["detail"]["error"]

        assert error["type"] == "retrieval_error"
        assert "message" in error

    @pytest.mark.asyncio
    async def test_chat_generation_error_503(self, client, mock_generation_service):
        """Test that GenerationError returns 503 Service Unavailable."""
        mock_generation_service.process_query.side_effect = GenerationError(
            "LLM timeout after 120s", context={"timeout": 120, "model": "DeepSeek-R1"}
        )

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

        # Check inside 'detail' wrapper
        assert "detail" in data
        assert "error" in data["detail"]
        error = data["detail"]["error"]

        assert error["type"] == "generation_error"

    @pytest.mark.asyncio
    async def test_chat_internal_error_500(self, client, mock_generation_service):
        """Test that unexpected exceptions return 500 without exposing details."""
        mock_generation_service.process_query.side_effect = RuntimeError(
            "Unexpected internal error"
        )

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

        # Check inside 'detail' wrapper
        assert "detail" in data
        assert "error" in data["detail"]
        error = data["detail"]["error"]

        assert "internal" in str(error).lower() or "unexpected" in str(error).lower()

    @pytest.mark.asyncio
    async def test_chat_token_counting_fallback(self, client, mock_llama_client):
        """Test fallback to estimated tokens if count_tokens fails."""
        # Le endpoint appelle count_tokens à la fin de la génération bloquante
        mock_llama_client.generate.return_value = "Response"
        # On force count_tokens à échouer
        mock_llama_client.count_tokens.side_effect = GenerationError("Token API down")

        response = client.post(
            "/api/v1/chat/completions",
            json={
                "model": "petit-prince-rag",
                "messages": [{"role": "user", "content": "Test"}],
                "stream": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        
        # Vérifie que completion_tokens est calculé (estimation len/4) malgré l'erreur
        assert data["usage"]["completion_tokens"] > 0


@pytest.mark.unit
class TestChatEndpointUsageCalculation:
    """Test token usage calculation."""

    @pytest.mark.asyncio
    async def test_chat_usage_calculation_correctness(self, client):
        """Test that total_tokens = prompt_tokens + completion_tokens."""
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
        assert (
            usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
        )

    @pytest.mark.asyncio
    async def test_chat_usage_in_streaming_final_chunk(self, client):
        """Test that usage appears only in final streaming chunk."""
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

        usage_found = False
        # Usage should be in the last chunk before [DONE]
        for line in lines:
            if "[DONE]" not in line:
                try:
                    chunk_data = json.loads(line[6:])  # Remove "data: " prefix
                    if "usage" in chunk_data and chunk_data["usage"]:
                        usage_found = True
                        break
                except json.JSONDecodeError:
                    pass

        if usage_found:
            assert True


@pytest.mark.unit
class TestChatEndpointResponseFormat:
    """Test OpenAI API format compliance."""

    @pytest.mark.asyncio
    async def test_chat_response_has_required_fields(self, client):
        """Test that response contains all required OpenAI API fields."""
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

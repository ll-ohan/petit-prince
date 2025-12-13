"""Integration tests for API endpoints.

Note: These tests require actual services (llama.cpp, Qdrant) to be running.
Run with: pytest tests/integration -v
"""

import pytest


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health endpoint (no dependencies)."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Health endpoint returns success."""
        # This test would use a FastAPI test client
        # from httpx import AsyncClient
        # from src.main import app
        #
        # async with AsyncClient(app=app, base_url="http://test") as client:
        #     response = await client.get("/health")
        #     assert response.status_code == 200
        #     assert response.json()["status"] == "healthy"
        pytest.skip("Requires test client setup")


@pytest.mark.integration
class TestInitEndpoint:
    """Test initialization endpoint."""

    @pytest.mark.asyncio
    async def test_init_with_valid_file(self):
        """Init with valid file succeeds."""
        # Would test full ingestion pipeline with real services
        pytest.skip("Requires running llama.cpp and Qdrant")

    @pytest.mark.asyncio
    @pytest.mark.edge_case
    async def test_init_with_empty_file(self):
        """Init with empty file returns 422."""
        pytest.skip("Requires test setup")


@pytest.mark.integration
class TestChatEndpoint:
    """Test chat endpoint."""

    @pytest.mark.asyncio
    async def test_chat_blocking(self):
        """Blocking chat returns valid response."""
        pytest.skip("Requires running services and indexed collection")

    @pytest.mark.asyncio
    async def test_chat_streaming(self):
        """Streaming chat returns SSE chunks."""
        pytest.skip("Requires running services and indexed collection")

    @pytest.mark.asyncio
    @pytest.mark.edge_case
    async def test_chat_with_empty_messages(self):
        """Empty messages array returns 422."""
        pytest.skip("Requires test setup")


# Example of a complete integration test (for reference)
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_rag_pipeline():
    """
    Full RAG pipeline test (requires all services).

    This would:
    1. Initialize collection with test data
    2. Submit a query
    3. Verify response format and content
    4. Check metrics
    """
    pytest.skip("Requires full service stack - implement when services are ready")

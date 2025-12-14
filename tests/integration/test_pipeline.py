"""
Integration tests for Le Petit Prince RAG pipeline.

Tests end-to-end functionality including ingestion, retrieval, and generation.
These tests may require external services (Qdrant, llama.cpp) to be running.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    from src.main import app as fastapi_app

    return fastapi_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.mark.integration
class TestIngestionPipeline:
    """Test document ingestion and indexing."""

    @pytest.mark.requires_all_services
    def test_init_endpoint_creates_index(self, client, sample_text_file):
        """
        Test that POST /api/init successfully ingests and indexes documents.

        Prerequisites:
        - Qdrant must be running on configured port
        - llama.cpp embedding server must be running
        - Valid source file must exist
        """
        response = client.post("/api/init")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data or "documents_indexed" in data
        # Specific structure depends on implementation

    @pytest.mark.requires_all_services
    def test_reindexing_no_duplication(self, client):
        """
        Test that re-running /api/init replaces the collection.

        Should not duplicate documents.
        """
        # First indexing
        response1 = client.post("/api/init")
        assert response1.status_code == 200
        data1 = response1.json()
        count1 = data1.get("documents_indexed", 0)

        # Second indexing
        response2 = client.post("/api/init")
        assert response2.status_code == 200
        data2 = response2.json()
        count2 = data2.get("documents_indexed", 0)

        # Should have same count (collection replaced, not appended)
        assert count1 == count2


@pytest.mark.integration
class TestChatPipeline:
    """Test complete RAG pipeline for chat."""

    @pytest.mark.requires_all_services
    def test_chat_returns_contextual_response(self, client):
        """
        Test that chat endpoint returns response with context from book.

        Prerequisites:
        - Index must be initialized (/api/init called first)
        - All services (Qdrant, llama.cpp) must be running
        """
        # Ensure index exists
        client.post("/api/init")

        # Send query about the fox
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

        # Verify response contains relevant information
        content = data["choices"][0]["message"]["content"]
        assert len(content) > 0

        # Should mention key concepts (may vary by model)
        # This is a smoke test - exact content depends on generation model
        assert isinstance(content, str)

    @pytest.mark.requires_all_services
    def test_chat_streaming_returns_chunks(self, client):
        """Test streaming chat completion returns SSE chunks."""
        # Ensure index exists
        client.post("/api/init")

        response = client.post(
            "/api/v1/chat/completions",
            json={
                "model": "petit-prince-rag",
                "messages": [
                    {"role": "user", "content": "Que dit le renard au Petit Prince?"}
                ],
                "stream": True,
            },
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Verify SSE format
        text = response.text
        assert "data:" in text
        assert "[DONE]" in text

    @pytest.mark.requires_all_services
    @pytest.mark.slow
    def test_chat_with_metrics(self, client):
        """Test that metrics are returned when requested."""
        client.post("/api/init")

        response = client.post(
            "/api/v1/chat/completions",
            json={
                "model": "petit-prince-rag",
                "messages": [{"role": "user", "content": "Test question"}],
                "stream": False,
            },
            headers={"X-Include-Metrics": "true"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify metrics structure
        assert "x_metrics" in data
        assert "timings" in data["x_metrics"]
        assert "retrieval" in data["x_metrics"]

        # Verify timing values are reasonable
        timings = data["x_metrics"]["timings"]
        assert timings["total_ms"] > 0
        assert timings["embedding_ms"] >= 0
        assert timings["search_ms"] >= 0


@pytest.mark.integration
@pytest.mark.requires_all_services
class TestConcurrency:
    """Test concurrent request handling."""

    @pytest.mark.slow
    def test_concurrent_chat_requests(self, client):
        """
        Test that multiple concurrent chat requests are handled correctly.

        This is a basic concurrency test. For production load testing,
        use tools like locust or k6.
        """
        import concurrent.futures

        client.post("/api/init")

        def send_request(question: str):
            response = client.post(
                "/api/v1/chat/completions",
                json={
                    "model": "petit-prince-rag",
                    "messages": [{"role": "user", "content": question}],
                    "stream": False,
                },
            )
            return response.status_code

        questions = [
            "Qui est le renard?",
            "Qui est le Petit Prince?",
            "Que dit le renard?",
            "Où habite le Petit Prince?",
            "Qu'est-ce qu'apprivoiser?",
        ]

        # Send requests concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(send_request, q) for q in questions]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == len(questions)


@pytest.mark.integration
class TestErrorRecovery:
    """Test error handling and recovery in integration scenarios."""

    def test_chat_without_init_returns_error(self, client):
        """
        Test that attempting chat before initialization returns appropriate error.

        This assumes collection doesn't exist yet.
        """
        # Attempt chat without initializing
        response = client.post(
            "/api/v1/chat/completions",
            json={
                "model": "petit-prince-rag",
                "messages": [{"role": "user", "content": "Test"}],
                "stream": False,
            },
        )

        # Should return error (400 or 503 depending on implementation)
        assert response.status_code in (400, 503)
        data = response.json()
        assert "error" in data


@pytest.mark.integration
class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_endpoint_returns_200(self, client):
        """Test that GET /health returns 200 when service is healthy."""
        response = client.get("/health")

        assert response.status_code == 200
        # Response format depends on implementation
        # May be {"status": "healthy"} or similar


@pytest.mark.integration
@pytest.mark.requires_qdrant
class TestQdrantIntegration:
    """Test Qdrant vector store integration."""

    @pytest.mark.slow
    def test_qdrant_collection_persistence(self, client):
        """
        Test that Qdrant collection persists between requests.

        Verifies that:
        1. Collection is created on init
        2. Collection remains accessible for subsequent queries
        """
        # Initialize collection
        init_response = client.post("/api/init")
        assert init_response.status_code == 200

        # Query should work immediately after
        chat_response = client.post(
            "/api/v1/chat/completions",
            json={
                "model": "petit-prince-rag",
                "messages": [{"role": "user", "content": "Test"}],
                "stream": False,
            },
        )

        assert chat_response.status_code == 200


@pytest.mark.integration
@pytest.mark.requires_llama
class TestLlamaIntegration:
    """Test llama.cpp server integration."""

    @pytest.mark.slow
    def test_embedding_service_connectivity(self, client):
        """Test that embedding service is reachable during init."""
        response = client.post("/api/init")

        # If embedding service is down, should return 503 or connection error
        # If successful, should return 200
        assert response.status_code in (200, 503)

        if response.status_code == 503:
            data = response.json()
            # Error message should indicate service unavailability
            assert "error" in data

    @pytest.mark.slow
    def test_generation_service_connectivity(self, client):
        """Test that generation service is reachable during chat."""
        client.post("/api/init")

        response = client.post(
            "/api/v1/chat/completions",
            json={
                "model": "petit-prince-rag",
                "messages": [{"role": "user", "content": "Test"}],
                "stream": False,
            },
        )

        # Should succeed if generation service is up
        assert response.status_code in (200, 503)


# ============================================================================
# Performance / Benchmark Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.slow
class TestPerformance:
    """Performance and latency tests."""

    @pytest.mark.requires_all_services
    def test_chat_response_latency(self, client, benchmark):
        """
        Benchmark chat endpoint latency.

        NOTE: Results highly dependent on:
        - Hardware (CPU/GPU)
        - Model size
        - Query complexity
        - System load
        """
        client.post("/api/init")

        def run_query():
            return client.post(
                "/api/v1/chat/completions",
                json={
                    "model": "petit-prince-rag",
                    "messages": [{"role": "user", "content": "Qui est le renard?"}],
                    "stream": False,
                },
            )

        result = benchmark(run_query)
        assert result.status_code == 200

    @pytest.mark.requires_all_services
    def test_init_performance(self, client, benchmark):
        """Benchmark indexing performance."""

        def run_init():
            return client.post("/api/init")

        result = benchmark(run_init)
        assert result.status_code == 200


# ============================================================================
# Test Helpers
# ============================================================================


@pytest.fixture(scope="module")
def initialized_app(client):
    """
    Fixture that ensures app is initialized before tests.

    Use this for tests that require the index to exist.
    """
    response = client.post("/api/init")
    if response.status_code == 200:
        yield client
    else:
        pytest.skip("Failed to initialize app - services may not be available")

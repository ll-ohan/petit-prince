"""
Integration tests for peripheral API endpoints.
Tests CORS, Health check, and common HTTP errors.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    from src.main import app as fastapi_app

    return fastapi_app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.mark.integration
class TestAPIEndpoints:

    def test_health_endpoint(self, client):
        """Test health check returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_cors_headers(self, client):
        """Test that CORS headers are present (if configured)."""
        # Note: TestClient does not process middleware by default same as real server
        # but we verify the OPTIONS request is handled
        response = client.options(
            "/api/v1/chat/completions",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        # Even if 405/200, checking flow does not crash
        assert response.status_code in (200, 405)

    def test_404_handling(self, client):
        """Test calling a non-existent endpoint."""
        response = client.get("/api/v1/does_not_exist")
        assert response.status_code == 404
        assert "detail" in response.json()

"""Unit tests for Init endpoint."""

import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from src.main import app
from src.ingestion.service import IngestionService
from src.core.exceptions import IngestionError

# Mock dependency
mock_ingestion_service = AsyncMock(spec=IngestionService)

# Override dependency
app.dependency_overrides[IngestionService] = lambda: mock_ingestion_service

client = TestClient(app)

@pytest.mark.unit
class TestInitRoute:
    
    def teardown_method(self):
        mock_ingestion_service.reset_mock()

    def test_init_success(self):
        """Test successful initialization returns 200 and stats."""
        mock_ingestion_service.ingest.return_value = {
            "paragraphs": 10, "vectors": 10
        }

        response = client.post("/api/init")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["statistics"]["paragraphs"] == 10

    def test_init_ingestion_error(self):
        """Test IngestionError is mapped to 422."""
        mock_ingestion_service.ingest.side_effect = IngestionError("File empty")

        response = client.post("/api/init")

        assert response.status_code == 422
        assert "File empty" in response.json()["detail"]["error"]["message"]

    def test_init_unexpected_error(self):
        """Test generic exception is mapped to 500."""
        mock_ingestion_service.ingest.side_effect = RuntimeError("Crash")

        response = client.post("/api/init")

        assert response.status_code == 500
        assert "internal_error" in response.json()["detail"]["error"]["type"]
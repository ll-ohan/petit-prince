"""Unit tests for Init endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.init import get_ingestion_service, get_settings
from src.core.exceptions import IngestionError
from src.ingestion.service import IngestionService


@pytest.fixture
def app():
    """Create FastAPI app instance for testing."""
    from src.main import app as fastapi_app

    return fastapi_app


@pytest.fixture
def mock_settings():
    """Mock application settings."""
    settings = MagicMock()
    # Mock specific settings accessed by the route
    settings.ingestion.source_file = "test_data.txt"
    settings.llama.embedding_dim = 1024
    return settings


@pytest.fixture
def mock_ingestion_service():
    """Mock IngestionService."""
    mock = AsyncMock(spec=IngestionService)
    return mock


@pytest.fixture
def client(app: FastAPI, mock_settings, mock_ingestion_service):
    """
    Create test client with mocked dependencies and startup logic.
    """
    # 1. Override dependencies used by the route
    app.dependency_overrides[get_settings] = lambda: mock_settings
    app.dependency_overrides[get_ingestion_service] = lambda: mock_ingestion_service

    # 2. Patch components used in src.main.lifespan to prevent real startup
    with (
        patch("src.main.Settings") as mocksettings,
        patch("src.main.LlamaClient") as mockllamainit,
        patch("src.main.QdrantRepository") as mockqdrantinit,
        patch("src.main.setup_logging"),
        patch("src.main.validate_config_at_startup"),
    ):

        # Configure mocks for lifespan
        mocksettings.from_yaml.return_value = mock_settings
        # Make close methods awaitable for lifespan shutdown
        mockllamainit.return_value.close = AsyncMock()
        mockqdrantinit.return_value.close = AsyncMock()

        with TestClient(app) as client:
            yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.mark.unit
class TestInitRoute:
    """Tests for /api/init endpoint."""

    def test_init_success(self, client, mock_ingestion_service):
        """Test successful initialization returns 200 and stats."""
        mock_ingestion_service.ingest.return_value = {"paragraphs": 10, "vectors": 10}

        response = client.post("/api/init")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["statistics"]["paragraphs"] == 10
        assert mock_ingestion_service.ingest.called

    def test_init_ingestion_error(self, client, mock_ingestion_service):
        """Test IngestionError is mapped to 422."""
        mock_ingestion_service.ingest.side_effect = IngestionError("File empty")

        response = client.post("/api/init")

        assert response.status_code == 422
        assert "File empty" in response.json()["detail"]["error"]["message"]

    def test_init_unexpected_error(self, client, mock_ingestion_service):
        """Test generic exception is mapped to 500."""
        mock_ingestion_service.ingest.side_effect = RuntimeError("Crash")

        response = client.post("/api/init")

        assert response.status_code == 500
        assert "internal_error" in response.json()["detail"]["error"]["type"]

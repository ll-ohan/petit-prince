"""Unit tests for IngestionService."""

import pytest
from unittest.mock import Mock, AsyncMock
from pathlib import Path
from src.ingestion.service import IngestionService

@pytest.fixture
def mock_components():
    return {
        "embedder": AsyncMock(),
        "vectorstore": AsyncMock(),
        "reader": Mock(),
        "chunker": Mock(),
        "builder": Mock()
    }

@pytest.fixture
def service(mock_components):
    svc = IngestionService(
        embedder=mock_components["embedder"],
        vectorstore=mock_components["vectorstore"],
        sentences_per_paragraph=2,
        batch_size=2
    )
    # Inject internal mocks
    svc.reader = mock_components["reader"]
    svc.chunker = mock_components["chunker"]
    svc.paragraph_builder = mock_components["builder"]
    return svc

@pytest.mark.unit
@pytest.mark.asyncio
class TestIngestionService:

    async def test_ingest_nominal_flow(self, service, mock_components):
        """Test complete ingestion pipeline execution."""
        # Setup mocks
        mock_components["reader"].read.return_value = "Raw Text"
        mock_components["chunker"].chunk.return_value = ["S1", "S2"]
        mock_components["builder"].build.return_value = ["P1"]
        mock_components["embedder"].embed_batch.return_value = [[0.1, 0.2]]
        
        stats = await service.ingest(Path("dummy.txt"), embedding_dim=2)

        # Verify flow
        mock_components["reader"].read.assert_called_once()
        mock_components["chunker"].chunk.assert_called_once()
        mock_components["builder"].build.assert_called_once()
        mock_components["vectorstore"].create_collection.assert_called_with(2)
        mock_components["embedder"].embed_batch.assert_called_once()
        mock_components["vectorstore"].upsert.assert_called_once()
        
        assert stats["paragraphs"] == 1
        assert stats["vectors"] == 1
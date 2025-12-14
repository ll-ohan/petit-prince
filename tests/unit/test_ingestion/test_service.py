"""Unit tests for IngestionService."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.exceptions import EmbeddingError, VectorStoreError
from src.ingestion.service import IngestionService


@pytest.fixture
def mock_components():
    return {
        "embedder": AsyncMock(),
        "vectorstore": AsyncMock(),
        "reader": Mock(),
        "chunker": Mock(),
        "builder": Mock(),
    }


@pytest.fixture
def service(mock_components):
    svc = IngestionService(
        embedder=mock_components["embedder"],
        vectorstore=mock_components["vectorstore"],
        sentences_per_paragraph=2,
        batch_size=2,
    )
    svc.reader = mock_components["reader"]
    svc.chunker = mock_components["chunker"]
    svc.paragraph_builder = mock_components["builder"]
    return svc


@pytest.mark.unit
@pytest.mark.asyncio
class TestIngestionService:

    async def test_ingest_nominal_flow(self, service, mock_components):
        """Test complete ingestion pipeline execution."""
        mock_components["reader"].read.return_value = "Raw Text"
        mock_components["chunker"].chunk.return_value = ["S1", "S2"]
        mock_components["builder"].build.return_value = ["P1"]
        mock_components["embedder"].embed_batch.return_value = [[0.1, 0.2]]

        stats = await service.ingest(Path("dummy.txt"), embedding_dim=2)

        mock_components["vectorstore"].create_collection.assert_called_with(2)
        mock_components["vectorstore"].upsert.assert_called_once()
        assert stats["paragraphs"] == 1

    async def test_ingest_embedder_failure(self, service, mock_components):
        """Test failure propagation from embedder."""
        mock_components["reader"].read.return_value = "Text"
        mock_components["chunker"].chunk.return_value = ["S1"]
        mock_components["builder"].build.return_value = ["P1"]
        mock_components["embedder"].embed_batch.side_effect = EmbeddingError("API Down")

        with pytest.raises(EmbeddingError):
            await service.ingest(Path("dummy.txt"), embedding_dim=2)

    async def test_ingest_vectorstore_failure(self, service, mock_components):
        """Test failure propagation from vectorstore upsert."""
        mock_components["reader"].read.return_value = "Text"
        mock_components["chunker"].chunk.return_value = ["S1"]
        mock_components["builder"].build.return_value = ["P1"]
        mock_components["embedder"].embed_batch.return_value = [[0.1]]
        mock_components["vectorstore"].upsert.side_effect = VectorStoreError("DB Full")

        with pytest.raises(VectorStoreError):
            await service.ingest(Path("dummy.txt"), embedding_dim=2)

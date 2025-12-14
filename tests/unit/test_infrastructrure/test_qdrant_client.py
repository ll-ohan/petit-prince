"""Unit tests for QdrantRepository."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.infrastructure.qdrant_client import QdrantRepository
from src.config.settings import QdrantConfig
from src.core.exceptions import VectorStoreError

@pytest.fixture
def qdrant_config():
    return QdrantConfig(
        host="localhost",
        port=6333,
        collection_name="test_coll",
        on_disk_payload=True,
        distance="Cosine"
    )

@pytest.fixture
def repo(qdrant_config):
    repo = QdrantRepository(qdrant_config)
    repo.client = AsyncMock() # Mock the internal AsyncQdrantClient
    return repo

@pytest.mark.unit
@pytest.mark.asyncio
class TestQdrantRepository:

    async def test_create_collection_idempotency(self, repo):
        """Test that existing collection is deleted before creation."""
        # Setup: Collection exists
        repo.client.get_collections.return_value = MagicMock(
            collections=[MagicMock(name="test_coll")]
        )

        await repo.create_collection(dimension=1024)

        # Verify delete called then create called
        repo.client.delete_collection.assert_called_with("test_coll")
        repo.client.create_collection.assert_called_once()

    async def test_upsert_success(self, repo):
        """Test successful upsert of vectors."""
        repo.client.upsert.return_value = MagicMock(status="completed")
        
        texts = ["text1", "text2"]
        vectors = [[0.1]*1024, [0.2]*1024]
        
        await repo.upsert(texts, vectors)
        
        repo.client.upsert.assert_called_once()
        call_args = repo.client.upsert.call_args
        assert len(call_args.kwargs['points']) == 2

    async def test_upsert_mismatch_error(self, repo):
        """Test error when texts and vectors lengths mismatch."""
        with pytest.raises(VectorStoreError):
            await repo.upsert(["text1"], []) # 1 text, 0 vectors

    async def test_search_mapping(self, repo):
        """Test mapping of Qdrant results to SearchResult."""
        mock_point = MagicMock()
        mock_point.payload = {"text": "found"}
        mock_point.score = 0.95
        
        repo.client.search.return_value = [mock_point]

        results = await repo.search([0.1]*1024, top_k=1)
        
        assert len(results) == 1
        assert results[0].text == "found"
        assert results[0].score == 0.95
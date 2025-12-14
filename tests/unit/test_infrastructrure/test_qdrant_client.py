"""Unit tests for QdrantRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config.settings import QdrantConfig
from src.core.exceptions import VectorStoreError
from src.infrastructure.qdrant_client import QdrantRepository


@pytest.fixture
def qdrant_config():
    return QdrantConfig(
        host="localhost",
        port=6333,
        collection_name="test_coll",
        on_disk_payload=True,
        distance="Cosine",
    )


@pytest.fixture
def repo(qdrant_config):
    repo = QdrantRepository(qdrant_config)
    repo.client = AsyncMock()  # Mock the internal AsyncQdrantClient
    return repo


@pytest.mark.unit
@pytest.mark.asyncio
class TestQdrantRepository:

    async def test_create_collection_idempotency(self, repo):
        """Test that existing collection is deleted before creation."""
        # Create a mock with the name attribute explicitly set
        collection_mock = MagicMock()
        collection_mock.name = "test_coll"

        repo.client.get_collections.return_value = MagicMock(
            collections=[collection_mock]
        )

        await repo.create_collection(dimension=1024)

        repo.client.delete_collection.assert_called_with("test_coll")
        repo.client.create_collection.assert_called_once()

    async def test_create_collection_failure(self, repo):
        """Test error handling when collection creation fails."""
        # Mock get_collections to return empty so creation proceeds
        repo.client.get_collections.return_value = MagicMock(collections=[])
        repo.client.create_collection.side_effect = Exception("API Error")

        with pytest.raises(VectorStoreError) as exc:
            await repo.create_collection(dimension=1024)
        assert "Failed to create collection" in str(exc.value)

    async def test_upsert_success(self, repo):
        """Test successful upsert of vectors."""
        repo.client.upsert.return_value = MagicMock(status="completed")

        texts = ["text1", "text2"]
        vectors = [[0.1] * 1024, [0.2] * 1024]

        await repo.upsert(texts, vectors)

        repo.client.upsert.assert_called_once()
        call_args = repo.client.upsert.call_args
        assert len(call_args.kwargs["points"]) == 2

    async def test_upsert_mismatch_error(self, repo):
        """Test error when texts and vectors lengths mismatch."""
        with pytest.raises(VectorStoreError):
            await repo.upsert(["text1"], [])  # 1 text, 0 vectors

    async def test_search_mapping(self, repo):
        """Test mapping of Qdrant results to SearchResult."""
        mock_point = MagicMock()
        mock_point.payload = {"text": "found"}
        mock_point.score = 0.95

        # The implementation uses query_points, not search
        repo.client.query_points.return_value = MagicMock(points=[mock_point])

        results = await repo.search([0.1] * 1024, top_k=1)

        assert len(results) == 1
        assert results[0].text == "found"
        assert results[0].score == 0.95

    async def test_search_connection_error(self, repo):
        """Test handling of connection errors during search."""
        # The implementation uses query_points
        repo.client.query_points.side_effect = Exception("Connection refused")

        with pytest.raises(VectorStoreError) as exc:
            await repo.search([0.1] * 1024, top_k=1)
        assert "Search failed" in str(exc.value)

    async def test_collection_exists_generic_error(self, repo):
        """Test collection_exists handles generic DB errors gracefully."""
        # Simule une panne DB lors de la vérification
        repo.client.get_collections.side_effect = Exception("DB Connection Fail")
        
        # Ne doit pas lever d'erreur, mais retourner False (et logger un warning)
        exists = await repo.collection_exists()
        assert exists is False

    async def test_upsert_generic_error(self, repo):
        """Test upsert wraps generic exceptions in VectorStoreError."""
        repo.client.upsert.side_effect = Exception("Unexpected DB Error")
        
        with pytest.raises(VectorStoreError) as exc:
            await repo.upsert(["text"], [[0.1]*1024])
        assert "Failed to upsert" in str(exc.value)

    async def test_search_generic_error(self, repo):
        """Test search wraps generic exceptions in VectorStoreError."""
        repo.client.query_points.side_effect = Exception("Search Crash")
        
        with pytest.raises(VectorStoreError) as exc:
            await repo.search([0.1]*1024, top_k=5)
        assert "Search failed" in str(exc.value)
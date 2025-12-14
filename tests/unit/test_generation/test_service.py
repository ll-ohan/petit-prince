"""Unit tests for GenerationService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.generation.service import GenerationService
from src.core.exceptions import RerankError
from src.generation.response_handler import RequestMetrics

@pytest.fixture
def service_mocks():
    return {
        "embedder": AsyncMock(),
        "vectorstore": AsyncMock(),
        "reranker": AsyncMock(),
        "generator": AsyncMock()
    }

@pytest.fixture
def service(service_mocks):
    return GenerationService(
        embedder=service_mocks["embedder"],
        vectorstore=service_mocks["vectorstore"],
        reranker=service_mocks["reranker"],
        generator=service_mocks["generator"],
        top_k=5, top_x=3, threshold=0.7
    )

@pytest.mark.unit
@pytest.mark.asyncio
class TestGenerationService:

    async def test_process_query_nominal(self, service, service_mocks):
        """Test standard RAG flow."""
        # Setup returns
        service_mocks["vectorstore"].search.return_value = [
            MagicMock(text="doc1", score=0.8)
        ]
        service_mocks["reranker"].rerank.return_value = [
            MagicMock(text="doc1", score=0.9)
        ]
        service_mocks["generator"].count_tokens.return_value = 10

        msgs, docs = await service.process_query(
            [{"role": "user", "content": "Q"}], RequestMetrics()
        )

        assert len(docs) == 1
        assert "doc1" in msgs[-1]["content"] # Context injected
        service_mocks["reranker"].rerank.assert_called_once()

    async def test_fallback_on_rerank_error(self, service, service_mocks):
        """Test fallback to vector search if reranker fails."""
        service_mocks["vectorstore"].search.return_value = [
            MagicMock(text="doc1", score=0.8)
        ]
        service_mocks["reranker"].rerank.side_effect = RerankError("Fail")

        _, docs = await service.process_query(
            [{"role": "user", "content": "Q"}], RequestMetrics()
        )

        # Should still have docs from vector search
        assert len(docs) == 1
        assert docs[0].score == 0.8  # Original vector score
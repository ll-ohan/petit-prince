"""Unit tests for GenerationService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exceptions import GenerationError, RerankError
from src.generation.response_handler import RequestMetrics
from src.generation.service import GenerationService


@pytest.fixture
def service_mocks():
    return {
        "embedder": AsyncMock(),
        "vectorstore": AsyncMock(),
        "reranker": AsyncMock(),
        "generator": AsyncMock(),
    }


@pytest.fixture
def service(service_mocks):
    return GenerationService(
        embedder=service_mocks["embedder"],
        vectorstore=service_mocks["vectorstore"],
        reranker=service_mocks["reranker"],
        generator=service_mocks["generator"],
        top_k=5,
        top_x=3,
        threshold=0.7,
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestGenerationService:

    async def test_process_query_nominal(self, service, service_mocks):
        """Test standard RAG flow."""
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
        assert "doc1" in msgs[-1]["content"]
        service_mocks["reranker"].rerank.assert_called_once()

    async def test_process_query_no_search_results(self, service, service_mocks):
        """Test flow stops if vector search returns nothing."""
        service_mocks["vectorstore"].search.return_value = []

        msgs, docs = await service.process_query(
            [{"role": "user", "content": "Q"}], RequestMetrics()
        )

        assert len(docs) == 0
        service_mocks["reranker"].rerank.assert_not_called()
        # Message original conservé sans contexte
        assert msgs[-1]["content"] == "Q"

    async def test_fallback_on_rerank_error(self, service, service_mocks):
        """Test fallback to vector search if reranker fails."""
        service_mocks["vectorstore"].search.return_value = [
            MagicMock(text="doc1", score=0.8)
        ]
        service_mocks["reranker"].rerank.side_effect = RerankError("Fail")

        _, docs = await service.process_query(
            [{"role": "user", "content": "Q"}], RequestMetrics()
        )

        assert len(docs) == 1
        assert docs[0].score == 0.8

    async def test_token_counting_failure(self, service, service_mocks):
        """Test fallback estimation when token counting fails."""
        # CORRECTION : Fournir des résultats pour passer l'étape 2 (Vector Search)
        service_mocks["vectorstore"].search.return_value = [
            MagicMock(text="doc1", score=0.8)
        ]
        # Fournir des résultats pour passer l'étape 3 (Rerank)
        service_mocks["reranker"].rerank.return_value = [
            MagicMock(text="doc1", score=0.9)
        ]

        # Simuler l'erreur de comptage
        service_mocks["generator"].count_tokens.side_effect = GenerationError("Fail")

        metrics = RequestMetrics()
        await service.process_query(
            [{"role": "user", "content": "Short query"}], metrics
        )

        # Maintenant l'estimation a lieu : len("Short query") // 4 > 0
        assert metrics.prompt_tokens > 0

"""Unit tests for LlamaClient."""

import pytest
import httpx
import math
from src.infrastructure.llama_client import LlamaClient
from src.config.settings import LlamaConfig
from src.core.exceptions import EmbeddingError, GenerationError, RerankError

@pytest.fixture
def llama_config():
    return LlamaConfig(
        base_url="http://localhost:8080",
        embedding_model="test-embed",
        embedding_dim=1024,
        reranker_model="test-rerank",
        generation_model="test-gen",
        timeout=10
    )

@pytest.fixture
def client(llama_config):
    return LlamaClient(llama_config)

@pytest.mark.unit
@pytest.mark.asyncio
class TestLlamaClient:
    
    async def test_embed_batch_success(self, client, httpx_mock):
        """Test successful batch embedding."""
        httpx_mock.add_response(
            url="http://localhost:8080/v1/embeddings",
            json={"data": [{"embedding": [0.1] * 1024}]}
        )

        vectors = await client.embed_batch(["test"])
        
        assert len(vectors) == 1
        assert len(vectors[0]) == 1024

    async def test_embed_dimension_mismatch(self, client, httpx_mock):
        """Test error when API returns wrong dimension."""
        httpx_mock.add_response(
            url="http://localhost:8080/v1/embeddings",
            json={"data": [{"embedding": [0.1] * 512}]} # 512 vs 1024 expected
        )

        with pytest.raises(EmbeddingError) as exc:
            await client.embed_batch(["test"])
        assert "dimension mismatch" in str(exc.value)

    async def test_embed_api_timeout(self, client, httpx_mock):
        """Test handling of API timeouts."""
        # Simuler une exception de timeout sur toutes les tentatives
        httpx_mock.add_exception(httpx.ReadTimeout("Timeout"))

        with pytest.raises(httpx.ReadTimeout):
            await client.embed_batch(["test"])

    async def test_embed_api_500_error(self, client, httpx_mock):
        """Test handling of internal server errors (retry then fail)."""
        httpx_mock.add_response(
            url="http://localhost:8080/v1/embeddings",
            status_code=500,
            text="Internal Server Error"
        )

        with pytest.raises(httpx.HTTPStatusError):
            await client.embed_batch(["test"])

    async def test_embed_nan_values(self, client, httpx_mock):
        """Test rejection of embeddings containing NaN/Inf."""
        httpx_mock.add_response(
            url="http://localhost:8080/v1/embeddings",
            json={"data": [{"embedding": [float('nan')] * 1024}]}
        )

        with pytest.raises(EmbeddingError) as exc:
            await client.embed_batch(["test"])
        assert "NaN or Inf" in str(exc.value)

    async def test_rerank_success(self, client, httpx_mock):
        """Test successful reranking."""
        httpx_mock.add_response(
            url="http://localhost:8080/v1/rerank",
            json={
                "results": [
                    {"index": 0, "relevance_score": 0.9},
                    {"index": 1, "relevance_score": 0.1}
                ]
            }
        )

        docs = ["doc1", "doc2"]
        ranked = await client.rerank("query", docs, top_n=2)
        
        assert len(ranked) == 2
        assert ranked[0].score == 0.9
        assert ranked[0].text == "doc1"

    async def test_generate_blocking_success(self, client, httpx_mock):
        """Test blocking generation."""
        httpx_mock.add_response(
            url="http://localhost:8080/v1/chat/completions",
            json={
                "choices": [{"message": {"content": "Hello world"}}]
            }
        )

        response = await client.generate([{"role": "user", "content": "Hi"}])
        assert response == "Hello world"

    async def test_generate_empty_response(self, client, httpx_mock):
        """Test handling of empty content from LLM."""
        httpx_mock.add_response(
            url="http://localhost:8080/v1/chat/completions",
            json={
                "choices": [{"message": {"content": ""}}]
            }
        )

        response = await client.generate([{"role": "user", "content": "Hi"}])
        assert response == ""

    async def test_generate_stream_success(self, client, httpx_mock):
        """Test streaming generation."""
        stream_content = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            'data: {"choices":[{"delta":{"content":" world"}}]}\n\n',
            'data: [DONE]\n\n'
        ]
        
        httpx_mock.add_response(
            url="http://localhost:8080/v1/chat/completions",
            stream=iter(stream_content)
        )

        chunks = []
        async for chunk in client.generate_stream([{"role": "user"}]):
            chunks.append(chunk)
            
        assert "".join(chunks) == "Hello world"
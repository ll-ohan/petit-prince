"""Unit tests for LlamaClient."""

import httpx
import pytest

from src.config.settings import LlamaConfig
from src.core.exceptions import EmbeddingError
from src.infrastructure.llama_client import LlamaClient


@pytest.fixture
def llama_config():
    return LlamaConfig(
        embedding_url="http://localhost:8080",
        rerank_url="http://localhost:8080",
        generation_url="http://localhost:8080",
        embedding_model="test-embed",
        embedding_dim=1024,
        reranker_model="test-rerank",
        generation_model="test-gen",
        timeout=10,
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
            json={"data": [{"embedding": [0.1] * 1024}]},
        )

        vectors = await client.embed_batch(["test"])

        assert len(vectors) == 1
        assert len(vectors[0]) == 1024

    async def test_embed_dimension_mismatch(self, client, httpx_mock):
        """Test error when API returns wrong dimension."""
        httpx_mock.add_response(
            url="http://localhost:8080/v1/embeddings",
            json={"data": [{"embedding": [0.1] * 512}]},  # 512 vs 1024 expected
        )

        with pytest.raises(EmbeddingError) as exc:
            await client.embed_batch(["test"])
        assert "dimension mismatch" in str(exc.value)

    async def test_embed_api_timeout(self, client, httpx_mock):
        """Test handling of API timeouts."""
        # Client retries 3 times, so we need 3 exceptions
        for _ in range(3):
            httpx_mock.add_exception(httpx.ReadTimeout("Timeout"))

        # The client wraps RequestError (parent of ReadTimeout) in EmbeddingError
        with pytest.raises(EmbeddingError) as exc:
            await client.embed_batch(["test"])

        # Verify the cause was indeed a timeout
        assert "ReadTimeout" in str(exc.value)

    async def test_embed_api_500_error(self, client, httpx_mock):
        """Test handling of internal server errors (retry then fail)."""
        # Client retries 3 times on 500 errors
        for _ in range(3):
            httpx_mock.add_response(
                url="http://localhost:8080/v1/embeddings",
                status_code=500,
                text="Internal Server Error",
            )

        # The client wraps HTTPStatusError in EmbeddingError
        with pytest.raises(EmbeddingError) as exc:
            await client.embed_batch(["test"])

        assert "status 500" in str(exc.value)

    async def test_embed_nan_values(self, client, httpx_mock):
        """Test rejection of embeddings containing NaN/Inf."""
        # We manually construct the JSON string because standard JSON (used by httpx)
        # does not support NaN, but Python's json.loads accepts it by default.
        # This simulates what a C++ server might return or what the client might parse.
        nan_vector = ",".join(["NaN"] * 1024)
        response_text = f'{{"data": [{{"embedding": [{nan_vector}]}}]}}'

        httpx_mock.add_response(
            url="http://localhost:8080/v1/embeddings",
            text=response_text,
            headers={"Content-Type": "application/json"},
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
                    {"index": 1, "relevance_score": 0.1},
                ]
            },
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
            json={"choices": [{"message": {"content": "Hello world"}}]},
        )

        response = await client.generate([{"role": "user", "content": "Hi"}])
        assert response == "Hello world"

    async def test_generate_empty_response(self, client, httpx_mock):
        """Test handling of empty content from LLM."""
        httpx_mock.add_response(
            url="http://localhost:8080/v1/chat/completions",
            json={"choices": [{"message": {"content": ""}}]},
        )

        response = await client.generate([{"role": "user", "content": "Hi"}])
        assert response == ""

    async def test_generate_stream_success(self, client, httpx_mock):
        """Test streaming generation."""
        stream_content = [
            b'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            b'data: {"choices":[{"delta":{"content":" world"}}]}\n\n',
            b"data: [DONE]\n\n",
        ]

        # Use add_callback to explicitly construct the Response with an async generator.
        # This ensures httpx creates an AsyncIteratorByteStream, which satisfies
        # the AsyncByteStream assertion in the AsyncClient.
        def custom_response(request):
            async def stream_generator():
                for chunk in stream_content:
                    yield chunk

            # Wrap the generator in a class that satisfies httpx.AsyncByteStream
            class AsyncIteratorStream(httpx.AsyncByteStream):
                def __init__(self, iterator):
                    self.iterator = iterator

                async def __aiter__(self):
                    async for chunk in self.iterator:
                        yield chunk

            return httpx.Response(
                status_code=200,
                headers={"Content-Type": "text/event-stream"},
                stream=AsyncIteratorStream(stream_generator()),
            )

        httpx_mock.add_callback(
            custom_response, url="http://localhost:8080/v1/chat/completions"
        )

        chunks = []
        async for chunk in client.generate_stream([{"role": "user"}]):
            chunks.append(chunk)

        assert "".join(chunks) == "Hello world"

    async def test_count_tokens_success(self, client, httpx_mock):
        """Test token counting endpoint."""
        httpx_mock.add_response(
            url="http://localhost:8080/tokenize",
            json={"tokens": [1, 2, 3, 4, 5]},
        )
        count = await client.count_tokens("test text")
        assert count == 5

    async def test_embed_batch_empty(self, client):
        """Test embed_batch with empty input returns immediately."""
        # Ne doit faire aucun appel API
        result = await client.embed_batch([])
        assert result == []

    async def test_rerank_empty_documents(self, client):
        """Test rerank with empty documents returns immediately."""
        # Ne doit faire aucun appel API
        result = await client.rerank("query", [], 5)
        assert result == []

    async def test_rerank_api_error(self, client, httpx_mock):
        """Test rerank raises RerankError on API failure."""
        from src.core.exceptions import RerankError
        
        # On enregistre la réponse 3 fois car le client va effectuer 3 tentatives (1 initiale + 2 retries)
        for _ in range(3):
            httpx_mock.add_response(
                url="http://localhost:8080/v1/rerank",
                status_code=500,
                text="Server Error"
            )

        with pytest.raises(RerankError) as exc:
            await client.rerank("query", ["doc"], 1)
        
        # Maintenant l'erreur finale sera bien basée sur le dernier statut 500 reçu
        assert "status 500" in str(exc.value)
    
    async def test_count_tokens_error(self, client, httpx_mock):
        """Test count_tokens failure wraps in GenerationError."""
        from src.core.exceptions import GenerationError
        
        httpx_mock.add_response(
            url="http://localhost:8080/tokenize",
            status_code=400
        )
        
        with pytest.raises(GenerationError):
            await client.count_tokens("text")

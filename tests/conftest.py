"""
Global pytest fixtures and configuration.

This module provides shared fixtures, test data, and configuration
for all test suites in the Le Petit Prince RAG project.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from faker import Faker
from qdrant_client import AsyncQdrantClient

# Initialize Faker for test data generation
fake = Faker(locale="fr_FR")


# ============================================================================
# Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for the entire test session.

    This prevents event loop creation/destruction overhead between tests
    and ensures consistent async behavior.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# File System Fixtures
# ============================================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for test file operations.

    Yields:
        Path to temporary directory that's automatically cleaned up.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_text_file(temp_dir: Path) -> Path:
    """
    Create a sample text file with French content.

    Returns:
        Path to file containing sample Le Petit Prince text.
    """
    content = """Le Petit Prince habitait une planète à peine plus grande que lui.
Il avait besoin d'un ami. Un jour, il rencontra un renard.
Le renard lui dit: "Apprivoise-moi." Le petit prince ne comprenait pas.
"Qu'est-ce que signifie apprivoiser?" demanda-t-il.
"C'est créer des liens," répondit le renard."""

    file_path = temp_dir / "sample.txt"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def empty_file(temp_dir: Path) -> Path:
    """Create an empty text file for testing edge cases."""
    file_path = temp_dir / "empty.txt"
    file_path.write_text("", encoding="utf-8")
    return file_path


@pytest.fixture
def whitespace_only_file(temp_dir: Path) -> Path:
    """Create a file containing only whitespace."""
    file_path = temp_dir / "whitespace.txt"
    file_path.write_text("   \n\t\n   ", encoding="utf-8")
    return file_path


@pytest.fixture
def noise_only_file(temp_dir: Path) -> Path:
    """Create a file containing only structural noise."""
    content = """Chapitre I
IV
23.
[Illustration: Le Petit Prince]
CHAPITRE II"""

    file_path = temp_dir / "noise.txt"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture
def invalid_encoding_file(temp_dir: Path) -> Path:
    """Create a file with Latin-1 encoding for fallback testing."""
    content = "Texte avec caractères spéciaux: àéèêô"
    file_path = temp_dir / "latin1.txt"
    file_path.write_bytes(content.encode("latin-1"))
    return file_path


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def valid_config_dict() -> dict:
    """
    Provide a valid configuration dictionary.

    Returns:
        Complete config matching config.yml schema.
    """
    return {
        "server": {
            "host": "0.0.0.0",
            "port": 8000
        },
        "llama": {
            "embedding_url": "http://localhost:8080",
            "embedding_model": "Qwen-Embedding",
            "embedding_dim": 1024,
            "rerank_url": "http://localhost:8081",
            "reranker_model": "Qwen-Reranker",
            "generation_url": "http://localhost:8082",
            "generation_model": "DeepSeek-R1",
            "batch_size": 32,
            "timeout": 120
        },
        "qdrant": {
            "host": "localhost",
            "port": 6333,
            "collection_name": "petit_prince_test",
            "on_disk_payload": True,
            "distance": "Cosine"
        },
        "ingestion": {
            "source_file": "var/data/LePetitPrince.txt",
            "sentences_per_paragraph": 10
        },
        "retrieval": {
            "top_k": 20,
            "top_x": 5,
            "relevance_threshold": 0.7
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
        }
    }


@pytest.fixture
def config_yaml_file(temp_dir: Path, valid_config_dict: dict) -> Path:
    """Create a valid config.yml file for testing."""
    import yaml

    config_path = temp_dir / "config.yml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(valid_config_dict, f)
    return config_path


@pytest.fixture
def invalid_yaml_file(temp_dir: Path) -> Path:
    """Create a malformed YAML file for error testing."""
    config_path = temp_dir / "invalid.yml"
    config_path.write_text("invalid: yaml: syntax: [unclosed", encoding="utf-8")
    return config_path


# ============================================================================
# Mock Data Fixtures
# ============================================================================


@pytest.fixture
def sample_sentences() -> list[str]:
    """Provide sample French sentences for chunking tests."""
    return [
        "Le Petit Prince habitait une planète.",
        "Il avait besoin d'un ami.",
        "Un jour, il rencontra un renard.",
        "Le renard lui dit: \"Apprivoise-moi.\"",
        "Le petit prince ne comprenait pas.",
        "\"Qu'est-ce que signifie apprivoiser?\" demanda-t-il.",
        "\"C'est créer des liens,\" répondit le renard.",
        "\"Tu deviens responsable de ce que tu as apprivoisé.\"",
        "Le petit prince réfléchit longuement.",
        "Il comprit la leçon du renard."
    ]


@pytest.fixture
def sample_paragraphs() -> list[str]:
    """Provide sample paragraphs for embedding tests."""
    return [
        "Le Petit Prince habitait une planète à peine plus grande que lui. "
        "Il avait besoin d'un ami. Un jour, il rencontra un renard.",

        "Le renard lui dit: \"Apprivoise-moi.\" Le petit prince ne comprenait pas. "
        "\"Qu'est-ce que signifie apprivoiser?\" demanda-t-il.",

        "\"C'est créer des liens,\" répondit le renard. "
        "\"Tu deviens responsable de ce que tu as apprivoisé.\""
    ]


@pytest.fixture
def sample_embeddings() -> list[list[float]]:
    """
    Provide sample embedding vectors.

    Returns:
        List of 1024-dimensional vectors for testing.
    """
    import random
    random.seed(42)

    return [
        [random.gauss(0, 1) for _ in range(1024)]
        for _ in range(3)
    ]


@pytest.fixture
def sample_search_results() -> list[dict]:
    """Provide sample Qdrant search results."""
    return [
        {
            "id": "doc-1",
            "score": 0.92,
            "payload": {"text": "Le renard lui dit: \"Apprivoise-moi.\""}
        },
        {
            "id": "doc-2",
            "score": 0.87,
            "payload": {"text": "C'est créer des liens."}
        },
        {
            "id": "doc-3",
            "score": 0.76,
            "payload": {"text": "Tu deviens responsable."}
        }
    ]


# ============================================================================
# HTTP Client Mocks
# ============================================================================


@pytest.fixture
def mock_httpx_client() -> MagicMock:
    """
    Provide a mocked httpx.AsyncClient.

    Returns:
        Mock client with common HTTP methods.
    """
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    return mock_client


@pytest.fixture
def mock_embedding_response() -> dict:
    """Provide a mock llama.cpp embedding API response."""
    return {
        "object": "list",
        "data": [
            {"object": "embedding", "embedding": [0.1] * 1024, "index": 0},
            {"object": "embedding", "embedding": [0.2] * 1024, "index": 1}
        ],
        "model": "Qwen-Embedding",
        "usage": {"prompt_tokens": 50, "total_tokens": 50}
    }


@pytest.fixture
def mock_rerank_response() -> dict:
    """Provide a mock llama.cpp rerank API response."""
    return {
        "object": "list",
        "results": [
            {"index": 0, "relevance_score": 0.92},
            {"index": 2, "relevance_score": 0.87},
            {"index": 1, "relevance_score": 0.76}
        ],
        "model": "Qwen-Reranker",
        "usage": {"prompt_tokens": 100, "total_tokens": 100}
    }


@pytest.fixture
def mock_generation_response() -> dict:
    """Provide a mock llama.cpp generation API response."""
    return {
        "id": "chatcmpl-test-123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "DeepSeek-R1",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Le renard est un personnage sage qui enseigne au Petit Prince."
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 1847,
            "completion_tokens": 234,
            "total_tokens": 2081
        }
    }


# ============================================================================
# Service Mocks
# ============================================================================


@pytest.fixture
def mock_qdrant_client() -> AsyncMock:
    """
    Provide a mocked Qdrant client.

    Returns:
        Mock with common Qdrant operations.
    """
    mock = AsyncMock(spec=AsyncQdrantClient)
    mock.get_collections.return_value = MagicMock(collections=[])
    mock.create_collection.return_value = True
    mock.delete_collection.return_value = True
    mock.upsert.return_value = MagicMock(status="completed")
    mock.search.return_value = []
    return mock


@pytest.fixture
def mock_embedder() -> AsyncMock:
    """Provide a mocked IEmbedder implementation."""
    from src.core.interfaces.embedder import IEmbedder

    mock = AsyncMock(spec=IEmbedder)
    mock.embed_query.return_value = [0.1] * 1024
    mock.embed_batch.return_value = [[0.1] * 1024, [0.2] * 1024]
    return mock


@pytest.fixture
def mock_reranker() -> AsyncMock:
    """Provide a mocked IReranker implementation."""
    from src.core.interfaces.reranker import IReranker

    mock = AsyncMock(spec=IReranker)
    mock.rerank.return_value = [
        MagicMock(text="doc1", score=0.92),
        MagicMock(text="doc2", score=0.87)
    ]
    return mock


@pytest.fixture
def mock_generator() -> AsyncMock:
    """Provide a mocked IGenerator implementation."""
    from src.core.interfaces.generator import IGenerator

    mock = AsyncMock(spec=IGenerator)
    mock.generate.return_value = "Generated response"

    async def mock_stream():
        for chunk in ["Gen", "erated", " response"]:
            yield chunk

    mock.generate_stream.return_value = mock_stream()
    return mock


@pytest.fixture
def mock_vectorstore() -> AsyncMock:
    """Provide a mocked IVectorStore implementation."""
    from src.core.interfaces.vectorstore import IVectorStore

    mock = AsyncMock(spec=IVectorStore)
    mock.create_collection.return_value = None
    mock.upsert_vectors.return_value = None
    mock.search.return_value = []
    return mock


# ============================================================================
# Test Data Factories
# ============================================================================


@pytest.fixture
def create_chat_request():
    """
    Factory fixture for creating chat request objects.

    Returns:
        Callable that creates ChatRequest instances.
    """
    def _create(
        messages: list[dict] | None = None,
        model: str = "petit-prince-rag",
        stream: bool = False
    ) -> dict:
        if messages is None:
            messages = [{"role": "user", "content": "Qui est le renard?"}]

        return {
            "model": model,
            "messages": messages,
            "stream": stream
        }

    return _create


# ============================================================================
# Performance Testing Fixtures
# ============================================================================


@pytest.fixture
def large_text_corpus(temp_dir: Path) -> Path:
    """
    Create a large text file for performance testing.

    Returns:
        Path to 1MB text file.
    """
    # Generate ~1MB of text
    sentences = [
        f"{fake.sentence()} " * 10
        for _ in range(1000)
    ]
    content = "\n".join(sentences)

    file_path = temp_dir / "large_corpus.txt"
    file_path.write_text(content, encoding="utf-8")
    return file_path


# ============================================================================
# Cleanup and Teardown
# ============================================================================


@pytest.fixture(autouse=True)
async def cleanup_async_resources():
    """
    Automatically cleanup async resources after each test.

    This prevents resource leaks and ensures clean test isolation.
    """
    yield
    # Close any lingering httpx clients, database connections, etc.
    await asyncio.sleep(0.01)  # Allow pending tasks to complete


@pytest.fixture(scope="session", autouse=True)
def configure_test_logging():
    """Configure logging for test execution."""
    import logging

    # Reduce noise from httpx/httpcore during tests
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)

    yield

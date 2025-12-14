"""
Unit tests for configuration loading and validation - Valid cases.

Tests the successful loading and merging of configuration from YAML files
and environment variables, following the priority chain ENV > .env > .yml.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.config.settings import (
    IngestionConfig,
    LlamaConfig,
    LoggingConfig,
    QdrantConfig,
    RetrievalConfig,
    ServerConfig,
    Settings,
)


@pytest.mark.unit
class TestLlamaConfig:
    """Test LlamaConfig model validation."""

    def test_valid_llama_config(self):
        """Test creation of valid LlamaConfig."""
        config = LlamaConfig(
            base_url="http://localhost:8080",
            embedding_model="Qwen-Embedding",
            embedding_dim=1024,
            reranker_model="Qwen-Reranker",
            generation_model="DeepSeek-R1",
            batch_size=32,
            timeout=120,
        )

        assert config.base_url == "http://localhost:8080"
        assert config.embedding_dim == 1024
        assert config.batch_size == 32
        assert config.timeout == 120

    def test_url_trailing_slash_removed(self):
        """Test that trailing slashes are removed from base_url."""
        config = LlamaConfig(
            base_url="http://localhost:8080/",
            embedding_model="test",
            embedding_dim=768,
            reranker_model="test",
            generation_model="test",
        )

        assert config.base_url == "http://localhost:8080"

    def test_https_url_accepted(self):
        """Test that HTTPS URLs are accepted."""
        config = LlamaConfig(
            base_url="https://secure-server.com",
            embedding_model="test",
            embedding_dim=768,
            reranker_model="test",
            generation_model="test",
        )

        assert config.base_url == "https://secure-server.com"

    def test_default_batch_size_and_timeout(self):
        """Test that default values are applied for optional fields."""
        config = LlamaConfig(
            base_url="http://localhost:8080",
            embedding_model="test",
            embedding_dim=768,
            reranker_model="test",
            generation_model="test",
        )

        assert config.batch_size == 32
        assert config.timeout == 120


@pytest.mark.unit
class TestQdrantConfig:
    """Test QdrantConfig model validation."""

    def test_valid_qdrant_config(self):
        """Test creation of valid QdrantConfig."""
        config = QdrantConfig(
            host="localhost",
            port=6333,
            collection_name="petit_prince_test",
            on_disk_payload=True,
            distance="Cosine",
        )

        assert config.host == "localhost"
        assert config.port == 6333
        assert config.collection_name == "petit_prince_test"
        assert config.distance == "Cosine"

    @pytest.mark.parametrize(
        "collection_name",
        [
            "valid_name",
            "petit_prince",
            "test_collection_123",
            "a",
            "_private_collection",
        ],
    )
    def test_valid_collection_names(self, collection_name: str):
        """Test that valid collection names are accepted."""
        config = QdrantConfig(
            host="localhost", port=6333, collection_name=collection_name
        )

        assert config.collection_name == collection_name

    @pytest.mark.parametrize("distance", ["Cosine", "Euclid", "Dot"])
    def test_all_distance_metrics(self, distance: str):
        """Test that all supported distance metrics are accepted."""
        config = QdrantConfig(
            host="localhost", port=6333, collection_name="test", distance=distance
        )

        assert config.distance == distance


@pytest.mark.unit
class TestRetrievalConfig:
    """Test RetrievalConfig model validation."""

    def test_valid_retrieval_config(self):
        """Test creation of valid RetrievalConfig."""
        config = RetrievalConfig(top_k=20, top_x=5, relevance_threshold=0.7)

        assert config.top_k == 20
        assert config.top_x == 5
        assert config.relevance_threshold == 0.7

    def test_top_x_equals_top_k(self):
        """Test that top_x can equal top_k."""
        config = RetrievalConfig(top_k=10, top_x=10, relevance_threshold=0.5)

        assert config.top_k == 10
        assert config.top_x == 10

    def test_default_values(self):
        """Test that default values are applied."""
        config = RetrievalConfig()

        assert config.top_k == 20
        assert config.top_x == 5
        assert config.relevance_threshold == 0.7

    @pytest.mark.parametrize("threshold", [0.0, 0.5, 0.9, 1.0])
    def test_relevance_threshold_boundaries(self, threshold: float):
        """Test threshold at boundary values."""
        config = RetrievalConfig(relevance_threshold=threshold)

        assert config.relevance_threshold == threshold


@pytest.mark.unit
class TestIngestionConfig:
    """Test IngestionConfig model validation."""

    def test_valid_ingestion_config(self, sample_text_file: Path):
        """Test creation of valid IngestionConfig with existing file."""
        config = IngestionConfig(
            source_file=sample_text_file, sentences_per_paragraph=10
        )

        assert config.source_file == sample_text_file
        assert config.sentences_per_paragraph == 10

    def test_default_sentences_per_paragraph(self, sample_text_file: Path):
        """Test default value for sentences_per_paragraph."""
        config = IngestionConfig(source_file=sample_text_file)

        assert config.sentences_per_paragraph == 10


@pytest.mark.unit
class TestServerConfig:
    """Test ServerConfig model validation."""

    def test_valid_server_config(self):
        """Test creation of valid ServerConfig."""
        config = ServerConfig(host="127.0.0.1", port=8080)

        assert config.host == "127.0.0.1"
        assert config.port == 8080

    def test_default_values(self):
        """Test default server configuration."""
        config = ServerConfig()

        assert config.host == "0.0.0.0"
        assert config.port == 8000


@pytest.mark.unit
class TestLoggingConfig:
    """Test LoggingConfig model validation."""

    def test_valid_logging_config(self):
        """Test creation of valid LoggingConfig."""
        config = LoggingConfig(level="DEBUG", format="%(message)s")

        assert config.level == "DEBUG"
        assert config.format == "%(message)s"

    @pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    def test_all_log_levels(self, level: str):
        """Test that all standard log levels are accepted."""
        config = LoggingConfig(level=level)

        assert config.level == level

    def test_default_values(self):
        """Test default logging configuration."""
        config = LoggingConfig()

        assert config.level == "INFO"
        assert "asctime" in config.format
        assert "levelname" in config.format


@pytest.mark.unit
class TestSettingsFromYAML:
    """Test Settings.from_yaml() method."""

    def test_load_from_valid_yaml(self, config_yaml_file: Path, sample_text_file: Path):
        """Test loading settings from a valid YAML file."""
        # Update YAML with valid source file
        with open(config_yaml_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        config_data["ingestion"]["source_file"] = str(sample_text_file)

        with open(config_yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        settings = Settings.from_yaml(config_yaml_file)

        assert settings.server.host == "0.0.0.0"
        assert settings.llama.embedding_dim == 1024
        assert settings.qdrant.collection_name == "petit_prince_test"
        assert settings.retrieval.top_k == 20

    def test_load_from_nonexistent_yaml_uses_defaults(self, temp_dir: Path):
        """Test that loading from nonexistent YAML returns empty dict (requires all required fields)."""
        nonexistent = temp_dir / "nonexistent.yml"

        # This should fail because required fields are missing
        with pytest.raises(Exception):  # Pydantic ValidationError
            Settings.from_yaml(nonexistent)

    def test_env_vars_override_yaml(
        self, config_yaml_file: Path, sample_text_file: Path, monkeypatch
    ):
        """Test that environment variables override YAML values."""
        # Update YAML with valid source file
        with open(config_yaml_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        config_data["ingestion"]["source_file"] = str(sample_text_file)

        with open(config_yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        # Set environment variable to override YAML
        monkeypatch.setenv("LLAMA__EMBEDDING_DIM", "2048")
        monkeypatch.setenv("RETRIEVAL__TOP_K", "50")

        settings = Settings.from_yaml(config_yaml_file)

        # ENV overrides should be applied
        assert settings.llama.embedding_dim == 2048
        assert settings.retrieval.top_k == 50

        # YAML values should remain for non-overridden fields
        assert settings.llama.embedding_model == "Qwen-Embedding"

    def test_partial_yaml_with_defaults(self, temp_dir: Path, sample_text_file: Path):
        """Test that partial YAML is merged with defaults."""
        partial_config = {
            "llama": {
                "base_url": "http://test:8080",
                "embedding_model": "test-model",
                "embedding_dim": 768,
                "reranker_model": "test-rerank",
                "generation_model": "test-gen",
            },
            "qdrant": {
                "host": "qdrant",
                "port": 6333,
                "collection_name": "test",
            },
            "ingestion": {"source_file": str(sample_text_file)},
        }

        yaml_path = temp_dir / "partial.yml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(partial_config, f)

        settings = Settings.from_yaml(yaml_path)

        # Explicit values should be used
        assert settings.llama.embedding_dim == 768

        # Defaults should be applied for missing fields
        assert settings.retrieval.top_k == 20  # Default
        assert settings.logging.level == "INFO"  # Default


@pytest.mark.unit
class TestSettingsIntegration:
    """Test complete Settings model with all sub-configs."""

    def test_complete_valid_settings(self, sample_text_file: Path):
        """Test creation of complete valid Settings object."""
        settings = Settings(
            server=ServerConfig(host="0.0.0.0", port=8000),
            llama=LlamaConfig(
                base_url="http://localhost:8080",
                embedding_model="Qwen",
                embedding_dim=1024,
                reranker_model="Qwen-Rerank",
                generation_model="DeepSeek",
            ),
            qdrant=QdrantConfig(
                host="localhost", port=6333, collection_name="test_collection"
            ),
            retrieval=RetrievalConfig(top_k=20, top_x=5, relevance_threshold=0.7),
            ingestion=IngestionConfig(
                source_file=sample_text_file, sentences_per_paragraph=10
            ),
            logging=LoggingConfig(level="INFO"),
        )

        assert settings.server.port == 8000
        assert settings.llama.embedding_dim == 1024
        assert settings.qdrant.collection_name == "test_collection"
        assert settings.retrieval.top_x == 5
        assert settings.ingestion.source_file == sample_text_file
        assert settings.logging.level == "INFO"

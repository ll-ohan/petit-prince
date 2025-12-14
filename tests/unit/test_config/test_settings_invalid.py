"""
Unit tests for configuration validation - Invalid and edge cases.

Tests error handling for invalid configuration values, malformed YAML,
missing files, and logical inconsistencies.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config.settings import (
    IngestionConfig,
    LlamaConfig,
    QdrantConfig,
    RetrievalConfig,
    Settings,
)
from src.core.exceptions import ConfigurationError


@pytest.mark.unit
@pytest.mark.edge_case
class TestLlamaConfigInvalid:
    """Test LlamaConfig validation errors."""

    def test_invalid_url_format(self):
        """Test that invalid URL format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LlamaConfig(
                embedding_url="not-a-url",
                rerank_url="http://localhost:8080",
                generation_url="http://localhost:8080",
                embedding_model="test",
                embedding_dim=768,
                reranker_model="test",
                generation_model="test",
            )

        error_msg = str(exc_info.value)
        assert "must start with http://" in error_msg or "https://" in error_msg

    def test_ftp_url_rejected(self):
        """Test that non-HTTP protocols are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LlamaConfig(
                embedding_url="ftp://server.com",
                rerank_url="http://localhost:8080",
                generation_url="http://localhost:8080",
                embedding_model="test",
                embedding_dim=768,
                reranker_model="test",
                generation_model="test",
            )

        assert "must start with http://" in str(exc_info.value)

    @pytest.mark.parametrize(
        "dim,expected_error",
        [
            (0, "greater than 0"),
            (-1, "greater than 0"),
            (-100, "greater than 0"),
            (8193, "less than or equal to 8192"),
            (10000, "less than or equal to 8192"),
        ],
    )
    def test_invalid_embedding_dim(self, dim: int, expected_error: str):
        """Test that invalid embedding dimensions are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LlamaConfig(
                embedding_url="http://localhost:8080",
                rerank_url="http://localhost:8080",
                generation_url="http://localhost:8080",
                embedding_model="test",
                embedding_dim=dim,
                reranker_model="test",
                generation_model="test",
            )

        assert expected_error in str(exc_info.value)

    @pytest.mark.parametrize(
        "batch_size,expected_error",
        [
            (0, "greater than 0"),
            (-1, "greater than 0"),
            (513, "less than or equal to 512"),
            (1000, "less than or equal to 512"),
        ],
    )
    def test_invalid_batch_size(self, batch_size: int, expected_error: str):
        """Test that invalid batch sizes are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LlamaConfig(
                embedding_url="http://localhost:8080",
                rerank_url="http://localhost:8080",
                generation_url="http://localhost:8080",
                embedding_model="test",
                embedding_dim=768,
                reranker_model="test",
                generation_model="test",
                batch_size=batch_size,
            )

        assert expected_error in str(exc_info.value)

    @pytest.mark.parametrize(
        "timeout,expected_error",
        [
            (0, "greater than 0"),
            (-1, "greater than 0"),
            (601, "less than or equal to 600"),
            (10000, "less than or equal to 600"),
        ],
    )
    def test_invalid_timeout(self, timeout: int, expected_error: str):
        """Test that invalid timeouts are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LlamaConfig(
                embedding_url="http://localhost:8080",
                rerank_url="http://localhost:8080",
                generation_url="http://localhost:8080",
                embedding_model="test",
                embedding_dim=768,
                reranker_model="test",
                generation_model="test",
                timeout=timeout,
            )

        assert expected_error in str(exc_info.value)

    def test_empty_model_name(self):
        """Test that empty model names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            LlamaConfig(
                embedding_url="http://localhost:8080",
                rerank_url="http://localhost:8080",
                generation_url="http://localhost:8080",
                embedding_model="",
                embedding_dim=768,
                reranker_model="test",
                generation_model="test",
            )

        assert "at least 1 character" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.edge_case
class TestQdrantConfigInvalid:
    """Test QdrantConfig validation errors."""

    @pytest.mark.parametrize(
        "port,expected_error",
        [
            (0, "greater than 0"),
            (-1, "greater than 0"),
            (65536, "less than 65536"),
            (100000, "less than 65536"),
        ],
    )
    def test_invalid_port(self, port: int, expected_error: str):
        """Test that invalid ports are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QdrantConfig(host="localhost", port=port, collection_name="test")

        assert expected_error in str(exc_info.value)

    @pytest.mark.parametrize(
        "collection_name",
        [
            "Invalid-Name",  # Uppercase and dash
            "123invalid",  # Starts with number
            "name with spaces",  # Spaces
            "name-with-dashes",  # Dashes
            "",  # Empty
            "CamelCase",  # Uppercase
        ],
    )
    def test_invalid_collection_name(self, collection_name: str):
        """Test that invalid collection names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QdrantConfig(host="localhost", port=6333, collection_name=collection_name)

        error_msg = str(exc_info.value)
        # Should fail pattern validation or min_length
        assert "String should match pattern" in error_msg or "at least 1" in error_msg

    def test_invalid_distance_metric(self):
        """Test that invalid distance metrics are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QdrantConfig(
                host="localhost",
                port=6333,
                collection_name="test",
                distance="Manhattan",  # Not in allowed list
            )

        assert "Input should be 'Cosine', 'Euclid' or 'Dot'" in str(exc_info.value)

    def test_empty_host(self):
        """Test that empty host is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            QdrantConfig(host="", port=6333, collection_name="test")

        assert "at least 1 character" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.edge_case
class TestRetrievalConfigInvalid:
    """Test RetrievalConfig validation errors."""

    def test_top_x_greater_than_top_k(self):
        """Test that top_x > top_k raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RetrievalConfig(top_k=5, top_x=10, relevance_threshold=0.7)

        error_msg = str(exc_info.value)
        assert "top_x" in error_msg
        assert "must be <=" in error_msg
        assert "top_k" in error_msg

    @pytest.mark.parametrize(
        "top_k,expected_error",
        [
            (0, "greater than 0"),
            (-1, "greater than 0"),
            (1001, "less than or equal to 1000"),
            (5000, "less than or equal to 1000"),
        ],
    )
    def test_invalid_top_k(self, top_k: int, expected_error: str):
        """Test that invalid top_k values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RetrievalConfig(top_k=top_k, top_x=5, relevance_threshold=0.7)

        assert expected_error in str(exc_info.value)

    @pytest.mark.parametrize(
        "top_x,expected_error",
        [
            (0, "greater than 0"),
            (-1, "greater than 0"),
            (101, "less than or equal to 100"),
            (500, "less than or equal to 100"),
        ],
    )
    def test_invalid_top_x(self, top_x: int, expected_error: str):
        """Test that invalid top_x values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RetrievalConfig(top_k=100, top_x=top_x, relevance_threshold=0.7)

        assert expected_error in str(exc_info.value)

    @pytest.mark.parametrize(
        "threshold,expected_error",
        [
            (-0.1, "greater than or equal to 0"),
            (-1.0, "greater than or equal to 0"),
            (1.1, "less than or equal to 1"),
            (2.0, "less than or equal to 1"),
        ],
    )
    def test_invalid_relevance_threshold(self, threshold: float, expected_error: str):
        """Test that thresholds outside [0, 1] are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RetrievalConfig(top_k=20, top_x=5, relevance_threshold=threshold)

        assert expected_error in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.edge_case
class TestIngestionConfigInvalid:
    """Test IngestionConfig validation errors."""

    def test_nonexistent_source_file(self, temp_dir: Path):
        """Test that nonexistent source file raises ValidationError."""
        nonexistent = temp_dir / "does_not_exist.txt"

        with pytest.raises(ValidationError) as exc_info:
            IngestionConfig(source_file=nonexistent, sentences_per_paragraph=10)

        error_msg = str(exc_info.value)
        assert "Source file does not exist" in error_msg
        assert str(nonexistent) in error_msg

    def test_directory_instead_of_file(self, temp_dir: Path):
        """Test that directory path raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            IngestionConfig(source_file=temp_dir, sentences_per_paragraph=10)

        error_msg = str(exc_info.value)
        assert "Source path is not a file" in error_msg

    @pytest.mark.parametrize(
        "sentences,expected_error",
        [
            (0, "greater than 0"),
            (-1, "greater than 0"),
            (101, "less than or equal to 100"),
            (500, "less than or equal to 100"),
        ],
    )
    def test_invalid_sentences_per_paragraph(
        self, sample_text_file: Path, sentences: int, expected_error: str
    ):
        """Test that invalid sentences_per_paragraph values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IngestionConfig(
                source_file=sample_text_file, sentences_per_paragraph=sentences
            )

        assert expected_error in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.edge_case
class TestSettingsFromYAMLInvalid:
    """Test Settings.from_yaml() error handling."""

    def test_invalid_yaml_syntax(self, invalid_yaml_file: Path):
        """Test that malformed YAML raises ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            Settings.from_yaml(invalid_yaml_file)

        error = exc_info.value
        assert "Invalid YAML" in str(error)
        assert str(invalid_yaml_file) in str(error)

    def test_missing_required_fields(self, temp_dir: Path):
        """Test that YAML missing required fields raises ConfigurationError."""
        import yaml

        incomplete_config = {
            "server": {"host": "0.0.0.0", "port": 8000},
            # Missing: llama, qdrant, ingestion (all required)
        }

        yaml_path = temp_dir / "incomplete.yml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(incomplete_config, f)

        with pytest.raises(ConfigurationError) as exc_info:
            Settings.from_yaml(yaml_path)

        assert "Configuration validation failed" in str(exc_info.value)

    def test_invalid_field_types(self, temp_dir: Path, sample_text_file: Path):
        """Test that invalid field types raise ConfigurationError."""
        import yaml

        invalid_config = {
            "server": {"host": "0.0.0.0", "port": "not-a-number"},  # Invalid type
            "llama": {
                "embedding_url": "http://localhost:8080",
                "rerank_url": "http://localhost:8080",
                "generation_url": "http://localhost:8080",
                "embedding_model": "test",
                "embedding_dim": "also-not-a-number",  # Invalid type
                "reranker_model": "test",
                "generation_model": "test",
            },
            "qdrant": {"host": "localhost", "port": 6333, "collection_name": "test"},
            "ingestion": {"source_file": str(sample_text_file)},
        }

        yaml_path = temp_dir / "invalid_types.yml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(invalid_config, f)

        with pytest.raises(ConfigurationError) as exc_info:
            Settings.from_yaml(yaml_path)

        assert "Configuration validation failed" in str(exc_info.value)

    def test_configuration_with_nonexistent_source_file(self, temp_dir: Path):
        """Test that config with nonexistent source file raises error."""
        import yaml

        config = {
            "llama": {
                "embedding_url": "http://localhost:8080",
                "rerank_url": "http://localhost:8080",
                "generation_url": "http://localhost:8080",
                "embedding_model": "test",
                "embedding_dim": 768,
                "reranker_model": "test",
                "generation_model": "test",
            },
            "qdrant": {"host": "localhost", "port": 6333, "collection_name": "test"},
            "ingestion": {
                "source_file": "/path/to/nonexistent/file.txt",
                "sentences_per_paragraph": 10,
            },
        }

        yaml_path = temp_dir / "bad_source.yml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f)

        with pytest.raises(ConfigurationError) as exc_info:
            Settings.from_yaml(yaml_path)

        error_msg = str(exc_info.value)
        assert (
            "Configuration validation failed" in error_msg
            or "does not exist" in error_msg
        )


@pytest.mark.unit
@pytest.mark.edge_case
class TestConfigurationEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_max_embedding_dim_boundary(self):
        """Test that embedding_dim=8192 is accepted (boundary)."""
        config = LlamaConfig(
            embedding_url="http://localhost:8080",
            rerank_url="http://localhost:8080",
            generation_url="http://localhost:8080",
            embedding_model="test",
            embedding_dim=8192,  # Maximum allowed
            reranker_model="test",
            generation_model="test",
        )

        assert config.embedding_dim == 8192

    def test_min_embedding_dim_boundary(self):
        """Test that embedding_dim=1 is accepted (boundary)."""
        config = LlamaConfig(
            embedding_url="http://localhost:8080",
            rerank_url="http://localhost:8080",
            generation_url="http://localhost:8080",
            embedding_model="test",
            embedding_dim=1,  # Minimum allowed
            reranker_model="test",
            generation_model="test",
        )

        assert config.embedding_dim == 1

    def test_max_port_boundary(self):
        """Test that port=65535 is accepted (boundary)."""
        config = QdrantConfig(
            host="localhost", port=65535, collection_name="test"  # Maximum allowed
        )

        assert config.port == 65535

    def test_min_port_boundary(self):
        """Test that port=1 is accepted (boundary)."""
        config = QdrantConfig(host="localhost", port=1, collection_name="test")

        assert config.port == 1

    def test_context_preservation_in_configuration_error(self, invalid_yaml_file: Path):
        """Test that ConfigurationError preserves context information."""
        with pytest.raises(ConfigurationError) as exc_info:
            Settings.from_yaml(invalid_yaml_file)

        error = exc_info.value
        assert error.context is not None
        assert "yaml_path" in error.context
        assert str(invalid_yaml_file) in error.context["yaml_path"]

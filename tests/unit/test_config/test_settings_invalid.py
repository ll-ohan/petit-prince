"""Tests for invalid configuration validation."""

import pytest
from pydantic import ValidationError

from src.config.settings import Settings
from src.core.exceptions import ConfigurationError


class TestConfigValidation:
    """Test configuration validation catches error cases."""

    @pytest.mark.edge_case
    def test_missing_required_section(self, tmp_path):
        """Config without required llama section raises error."""
        config_content = """
server:
  host: "127.0.0.1"
  port: 8000

qdrant:
  host: "localhost"
  port: 6333
  collection_name: "test"

ingestion:
  source_file: "tests/fixtures/sample_book.txt"
"""
        config_file = tmp_path / "config.yml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigurationError):
            Settings.from_yaml(config_file)

    @pytest.mark.edge_case
    def test_embedding_dim_zero(self, tmp_path):
        """embedding_dim=0 raises validation error."""
        config_content = """
llama:
  base_url: "http://localhost:8080"
  embedding_model: "TestModel"
  embedding_dim: 0
  reranker_model: "TestReranker"
  generation_model: "TestGenerator"

qdrant:
  host: "localhost"
  port: 6333
  collection_name: "test"

ingestion:
  source_file: "tests/fixtures/sample_book.txt"
"""
        config_file = tmp_path / "config.yml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigurationError):
            Settings.from_yaml(config_file)

    @pytest.mark.edge_case
    def test_embedding_dim_negative(self, tmp_path):
        """embedding_dim=-1 raises validation error."""
        config_content = """
llama:
  base_url: "http://localhost:8080"
  embedding_model: "TestModel"
  embedding_dim: -1
  reranker_model: "TestReranker"
  generation_model: "TestGenerator"

qdrant:
  host: "localhost"
  port: 6333
  collection_name: "test"

ingestion:
  source_file: "tests/fixtures/sample_book.txt"
"""
        config_file = tmp_path / "config.yml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigurationError):
            Settings.from_yaml(config_file)

    @pytest.mark.edge_case
    def test_top_x_greater_than_top_k(self, tmp_path):
        """top_x > top_k raises logical validation error."""
        config_content = """
llama:
  base_url: "http://localhost:8080"
  embedding_model: "TestModel"
  embedding_dim: 768
  reranker_model: "TestReranker"
  generation_model: "TestGenerator"

qdrant:
  host: "localhost"
  port: 6333
  collection_name: "test"

ingestion:
  source_file: "tests/fixtures/sample_book.txt"

retrieval:
  top_k: 5
  top_x: 10
"""
        config_file = tmp_path / "config.yml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigurationError) as exc_info:
            Settings.from_yaml(config_file)

        assert "top_x" in str(exc_info.value).lower()

    @pytest.mark.edge_case
    def test_invalid_distance_metric(self, tmp_path):
        """distance='Invalid' raises validation error with valid options."""
        config_content = """
llama:
  base_url: "http://localhost:8080"
  embedding_model: "TestModel"
  embedding_dim: 768
  reranker_model: "TestReranker"
  generation_model: "TestGenerator"

qdrant:
  host: "localhost"
  port: 6333
  collection_name: "test"
  distance: "Invalid"

ingestion:
  source_file: "tests/fixtures/sample_book.txt"
"""
        config_file = tmp_path / "config.yml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigurationError):
            Settings.from_yaml(config_file)

    @pytest.mark.edge_case
    def test_source_file_not_exists(self, tmp_path):
        """Non-existent source_file raises with path in message."""
        config_content = """
llama:
  base_url: "http://localhost:8080"
  embedding_model: "TestModel"
  embedding_dim: 768
  reranker_model: "TestReranker"
  generation_model: "TestGenerator"

qdrant:
  host: "localhost"
  port: 6333
  collection_name: "test"

ingestion:
  source_file: "/non/existent/file.txt"
"""
        config_file = tmp_path / "config.yml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigurationError) as exc_info:
            Settings.from_yaml(config_file)

        assert "exist" in str(exc_info.value).lower()

    @pytest.mark.edge_case
    def test_invalid_url_format(self, tmp_path):
        """Malformed base_url raises with format hint."""
        config_content = """
llama:
  base_url: "not-a-url"
  embedding_model: "TestModel"
  embedding_dim: 768
  reranker_model: "TestReranker"
  generation_model: "TestGenerator"

qdrant:
  host: "localhost"
  port: 6333
  collection_name: "test"

ingestion:
  source_file: "tests/fixtures/sample_book.txt"
"""
        config_file = tmp_path / "config.yml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigurationError) as exc_info:
            Settings.from_yaml(config_file)

        assert "http" in str(exc_info.value).lower()

    @pytest.mark.edge_case
    def test_port_out_of_range(self, tmp_path):
        """port=70000 raises with valid range."""
        config_content = """
llama:
  base_url: "http://localhost:8080"
  embedding_model: "TestModel"
  embedding_dim: 768
  reranker_model: "TestReranker"
  generation_model: "TestGenerator"

qdrant:
  host: "localhost"
  port: 70000
  collection_name: "test"

ingestion:
  source_file: "tests/fixtures/sample_book.txt"
"""
        config_file = tmp_path / "config.yml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigurationError):
            Settings.from_yaml(config_file)

    @pytest.mark.edge_case
    def test_invalid_collection_name(self, tmp_path):
        """Collection name with invalid chars raises error."""
        config_content = """
llama:
  base_url: "http://localhost:8080"
  embedding_model: "TestModel"
  embedding_dim: 768
  reranker_model: "TestReranker"
  generation_model: "TestGenerator"

qdrant:
  host: "localhost"
  port: 6333
  collection_name: "Invalid-Name!"

ingestion:
  source_file: "tests/fixtures/sample_book.txt"
"""
        config_file = tmp_path / "config.yml"
        config_file.write_text(config_content)

        with pytest.raises(ConfigurationError):
            Settings.from_yaml(config_file)

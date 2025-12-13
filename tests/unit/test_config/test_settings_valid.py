"""Tests for valid configuration loading."""

from pathlib import Path

import pytest

from src.config.settings import Settings


class TestValidConfiguration:
    """Test valid configuration loading."""

    def test_load_from_yaml(self, tmp_path):
        """Valid YAML config loads successfully."""
        config_file = Path("tests/fixtures/config_samples/valid_config.yml")
        settings = Settings.from_yaml(config_file)

        assert settings.server.host == "127.0.0.1"
        assert settings.server.port == 8001
        assert settings.llama.base_url == "http://localhost:8080"
        assert settings.llama.embedding_dim == 768
        assert settings.qdrant.collection_name == "test_collection"
        assert settings.retrieval.top_k == 10
        assert settings.retrieval.top_x == 3

    def test_env_overrides_yaml(self, tmp_path, monkeypatch):
        """Environment variables override YAML values."""
        config_file = Path("tests/fixtures/config_samples/valid_config.yml")

        # Set env override
        monkeypatch.setenv("LLAMA__EMBEDDING_DIM", "1024")
        monkeypatch.setenv("RETRIEVAL__TOP_K", "25")

        settings = Settings.from_yaml(config_file)

        # ENV values override YAML
        assert settings.llama.embedding_dim == 1024
        assert settings.retrieval.top_k == 25

        # Non-overridden values still from YAML
        assert settings.server.port == 8001

    def test_defaults_applied(self, tmp_path):
        """Default values are applied for optional fields."""
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
  collection_name: "test_collection"

ingestion:
  source_file: "tests/fixtures/sample_book.txt"
"""
        config_file = tmp_path / "config.yml"
        config_file.write_text(config_content)

        settings = Settings.from_yaml(config_file)

        # Defaults applied
        assert settings.server.host == "0.0.0.0"
        assert settings.server.port == 8000
        assert settings.llama.batch_size == 32
        assert settings.retrieval.top_k == 20
        assert settings.retrieval.top_x == 5
        assert settings.logging.level == "INFO"

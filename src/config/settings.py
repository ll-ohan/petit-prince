"""Configuration management with ENV > .env > .yml priority."""

import os
from pathlib import Path
from typing import Literal

import httpx
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.exceptions import ConfigurationError


class LlamaConfig(BaseModel):
    """Llama.cpp server configuration."""

    embedding_url: str = Field(description="Base URL for embeddings service")
    rerank_url: str = Field(description="Base URL for reranking service")
    generation_url: str = Field(description="Base URL for generation service")

    embedding_model: str = Field(min_length=1, description="Model name for embeddings")
    embedding_dim: int = Field(gt=0, le=8192, description="Embedding vector dimension")
    reranker_model: str = Field(min_length=1, description="Model name for reranking")
    generation_model: str = Field(min_length=1, description="Model name for generation")
    batch_size: int = Field(
        gt=0, le=512, default=32, description="Batch size for embeddings"
    )
    timeout: int = Field(
        gt=0, le=600, default=120, description="Request timeout in seconds"
    )

    @field_validator("embedding_url", "rerank_url", "generation_url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http:// or https://, got: {v}")
        return v.rstrip("/")


class QdrantConfig(BaseModel):
    """Qdrant vector database configuration."""

    host: str = Field(min_length=1, description="Qdrant host")
    port: int = Field(gt=0, lt=65536, description="Qdrant port")
    collection_name: str = Field(
        min_length=1,
        pattern=r"^[a-z_][a-z0-9_]*$",
        description="Collection name (lowercase, underscore separated)",
    )
    on_disk_payload: bool = Field(default=True, description="Store payloads on disk")
    distance: Literal["Cosine", "Euclid", "Dot"] = Field(
        default="Cosine", description="Distance metric"
    )


class RetrievalConfig(BaseModel):
    """Retrieval and reranking configuration."""

    top_k: int = Field(
        gt=0, le=1000, default=20, description="Initial vector search results"
    )
    top_x: int = Field(gt=0, le=100, default=5, description="Results after reranking")
    relevance_threshold: float = Field(
        ge=0.0, le=1.0, default=0.7, description="Threshold for high/moderate relevance"
    )

    @model_validator(mode="after")
    def validate_top_x_less_than_top_k(self) -> "RetrievalConfig":
        """Ensure top_x <= top_k."""
        if self.top_x > self.top_k:
            raise ValueError(
                f"top_x ({self.top_x}) must be <= top_k ({self.top_k}). "
                f"Set top_x to a value <= {self.top_k}, or increase top_k."
            )
        return self


class IngestionConfig(BaseModel):
    """Ingestion configuration."""

    source_file: Path = Field(description="Path to source text file")
    sentences_per_paragraph: int = Field(
        gt=0, le=100, default=10, description="Sentences per paragraph chunk"
    )

    @field_validator("source_file")
    @classmethod
    def validate_file_exists(cls, v: Path) -> Path:
        """Validate source file exists and is readable."""
        if not v.exists():
            raise ValueError(f"Source file does not exist: {v}")
        if not v.is_file():
            raise ValueError(f"Source path is not a file: {v}")
        return v


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(gt=0, lt=65536, default=8000, description="Server port")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    format: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
    )


class Settings(BaseSettings):
    """Application settings with ENV > .env > .yml priority."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    server: ServerConfig = Field(default_factory=ServerConfig)
    llama: LlamaConfig
    qdrant: QdrantConfig
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    ingestion: IngestionConfig
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml(cls, yaml_path: Path = Path("config.yml")) -> "Settings":
        """Load settings from YAML file, with ENV overrides."""
        try:
            if yaml_path.exists():
                with open(yaml_path, encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f) or {}
            else:
                yaml_data = {}

            # Merge YAML with environment variables
            merged_data = {}

            def merge_nested(prefix: str, data: dict) -> dict:
                result = data.copy()
                for key, value in data.items():
                    env_key = f"{prefix}__{key}".upper()
                    if env_key in os.environ:
                        env_value = os.environ[env_key]
                        if isinstance(value, int):
                            try:
                                result[key] = int(env_value)
                            except ValueError:
                                result[key] = env_value
                        elif isinstance(value, float):
                            try:
                                result[key] = float(env_value)
                            except ValueError:
                                result[key] = env_value
                        elif isinstance(value, bool):
                            result[key] = env_value.lower() in ("true", "1", "yes")
                        else:
                            result[key] = env_value
                return result

            for section in [
                "server",
                "llama",
                "qdrant",
                "retrieval",
                "ingestion",
                "logging",
            ]:
                if section in yaml_data:
                    merged_data[section] = merge_nested(section, yaml_data[section])
                elif section in yaml_data:
                    merged_data[section] = yaml_data[section]

            return cls(**merged_data if merged_data else yaml_data)

        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML in {yaml_path}: {e}",
                context={"yaml_path": str(yaml_path)},
            ) from e
        except Exception as e:
            raise ConfigurationError(
                f"Configuration validation failed: {e}",
                context={"yaml_path": str(yaml_path)},
            ) from e


def validate_config_at_startup(config: Settings) -> None:
    """Validate configuration and external dependencies at startup."""
    errors: list = []

    # Check connectivity for all 3 services
    # We check /health or root, accepting 404 as "service exists
    # but path not found" which is good enough for connectivity
    urls_to_check = [
        ("Embedding", config.llama.embedding_url),
        ("Reranking", config.llama.rerank_url),
        ("Generation", config.llama.generation_url),
    ]

    for name, url in urls_to_check:
        try:
            httpx.get(f"{url}/health", timeout=5)
            # 404 is acceptable (service reachable), connection error is not
            pass
        except httpx.RequestError as e:
            import logging

            logging.getLogger(__name__).warning(
                "Cannot reach %s service at %s: %s (this is OK if service starts later)",
                name,
                url,
                e,
            )

    if errors:
        raise ConfigurationError(
            f"Configuration validation failed with {len(errors)} error(s)",
            context={"errors": errors},
        )

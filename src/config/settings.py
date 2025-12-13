"""Configuration management with ENV > .env > .yml priority."""

import os
from pathlib import Path
from typing import Literal

import httpx
import yaml
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.exceptions import ConfigurationError


class LlamaConfig(BaseModel):
    """Llama.cpp server configuration."""

    base_url: str = Field(description="Base URL of llama.cpp server")
    embedding_model: str = Field(min_length=1, description="Model name for embeddings")
    embedding_dim: int = Field(gt=0, le=8192, description="Embedding vector dimension")
    reranker_model: str = Field(min_length=1, description="Model name for reranking")
    generation_model: str = Field(min_length=1, description="Model name for generation")
    batch_size: int = Field(gt=0, le=512, default=32, description="Batch size for embeddings")
    timeout: int = Field(gt=0, le=600, default=120, description="Request timeout in seconds")

    @field_validator("base_url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"base_url must start with http:// or https://, got: {v}")
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

    top_k: int = Field(gt=0, le=1000, default=20, description="Initial vector search results")
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

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")
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
        """Load settings from YAML file, with ENV overrides.

        Args:
            yaml_path: Path to YAML configuration file.

        Returns:
            Settings instance.

        Raises:
            ConfigurationError: If YAML is invalid or configuration fails validation.
        """
        try:
            if yaml_path.exists():
                with open(yaml_path, "r", encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f) or {}
            else:
                yaml_data = {}

            # Merge YAML with environment variables
            # Pydantic BaseSettings will read env vars and override YAML values
            # We need to temporarily set the yaml data as defaults

            # Store original env to restore later if needed
            original_env = os.environ.copy()

            # Create a dict to hold merged values
            merged_data = {}

            # Helper to merge nested configs
            def merge_nested(prefix: str, data: dict) -> dict:
                result = data.copy()
                for key, value in data.items():
                    env_key = f"{prefix}__{key}".upper()
                    if env_key in os.environ:
                        # Parse env var value
                        env_value = os.environ[env_key]
                        # Try to convert to appropriate type
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
                            result[key] = env_value.lower() in ('true', '1', 'yes')
                        else:
                            result[key] = env_value
                return result

            # Apply env overrides to each section
            for section in ['server', 'llama', 'qdrant', 'retrieval', 'ingestion', 'logging']:
                if section in yaml_data:
                    merged_data[section] = merge_nested(section, yaml_data[section])
                elif section in yaml_data:
                    merged_data[section] = yaml_data[section]

            # Create settings with merged data
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
    """Validate configuration and external dependencies at startup.

    Args:
        config: Settings instance to validate.

    Raises:
        ConfigurationError: If validation fails with detailed error context.
    """
    errors = []

    # File existence already validated by Pydantic

    # Service connectivity (optional check)
    try:
        response = httpx.get(f"{config.llama.base_url}/health", timeout=5)
        if response.status_code not in (200, 404):  # 404 ok if no /health endpoint
            errors.append(
                f"llama.cpp at {config.llama.base_url} returned status {response.status_code}"
            )
    except httpx.RequestError as e:
        # Warning only - service might not be ready yet
        import logging

        logging.getLogger(__name__).warning(
            "Cannot reach llama.cpp at %s: %s (this is OK if service starts later)",
            config.llama.base_url,
            e,
        )

    # Logical consistency (already validated by Pydantic model validators)

    if errors:
        raise ConfigurationError(
            f"Configuration validation failed with {len(errors)} error(s)",
            context={"errors": errors},
        )

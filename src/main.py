"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from src.api.router import router
from src.config.logging import setup_logging
from src.config.settings import Settings, validate_config_at_startup
from src.generation.service import GenerationService
from src.ingestion.service import IngestionService
from src.infrastructure.llama_client import LlamaClient
from src.infrastructure.qdrant_client import QdrantRepository

logger = logging.getLogger(__name__)

# Global state
_settings: Settings | None = None
_llama_client: LlamaClient | None = None
_qdrant_client: QdrantRepository | None = None


def get_settings() -> Settings:
    """Get application settings (dependency)."""
    if _settings is None:
        raise RuntimeError("Settings not initialized")
    return _settings


def get_llama_client(settings: Settings = Depends(get_settings)) -> LlamaClient:
    """Get Llama client (dependency)."""
    if _llama_client is None:
        raise RuntimeError("Llama client not initialized")
    return _llama_client


def get_qdrant_client(settings: Settings = Depends(get_settings)) -> QdrantRepository:
    """Get Qdrant client (dependency)."""
    if _qdrant_client is None:
        raise RuntimeError("Qdrant client not initialized")
    return _qdrant_client


def get_ingestion_service(
    llama_client: LlamaClient = Depends(get_llama_client),
    qdrant_client: QdrantRepository = Depends(get_qdrant_client),
    settings: Settings = Depends(get_settings),
) -> IngestionService:
    """Get ingestion service (dependency)."""
    return IngestionService(
        embedder=llama_client,
        vectorstore=qdrant_client,
        sentences_per_paragraph=settings.ingestion.sentences_per_paragraph,
        batch_size=settings.llama.batch_size,
    )


def get_generation_service(
    llama_client: LlamaClient = Depends(get_llama_client),
    qdrant_client: QdrantRepository = Depends(get_qdrant_client),
    settings: Settings = Depends(get_settings),
) -> GenerationService:
    """Get generation service (dependency)."""
    return GenerationService(
        embedder=llama_client,
        vectorstore=qdrant_client,
        reranker=llama_client,
        generator=llama_client,
        top_k=settings.retrieval.top_k,
        top_x=settings.retrieval.top_x,
        threshold=settings.retrieval.relevance_threshold,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global _settings, _llama_client, _qdrant_client

    # Startup
    logger.info("Starting Le Petit Prince RAG application")

    # Load configuration
    _settings = Settings.from_yaml()
    setup_logging(_settings.logging)

    logger.info("Configuration loaded successfully")
    logger.debug("Llama base URL: %s", _settings.llama.base_url)
    logger.debug("Qdrant host: %s:%d", _settings.qdrant.host, _settings.qdrant.port)

    # Validate configuration
    validate_config_at_startup(_settings)

    # Initialize clients
    _llama_client = LlamaClient(_settings.llama)
    _qdrant_client = QdrantRepository(_settings.qdrant)

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application")

    if _llama_client:
        await _llama_client.close()
    if _qdrant_client:
        await _qdrant_client.close()

    logger.info("Application shutdown complete")


app = FastAPI(
    title="Le Petit Prince RAG",
    description="RAG pipeline specialized in Le Petit Prince by Antoine de Saint-Exupéry",
    version="1.0.0",
    lifespan=lifespan,
)

# Override dependencies for the entire app
app.dependency_overrides[Settings] = get_settings
app.dependency_overrides[LlamaClient] = get_llama_client
app.dependency_overrides[QdrantRepository] = get_qdrant_client
app.dependency_overrides[IngestionService] = get_ingestion_service
app.dependency_overrides[GenerationService] = get_generation_service

# Include routes
app.include_router(router)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

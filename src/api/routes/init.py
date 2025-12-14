"""Init endpoint for indexation."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas.init import InitResponse
from src.config.settings import Settings
from src.core.exceptions import IngestionError
from src.ingestion.service import IngestionService

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency placeholders - these are overridden in main.py
def get_settings() -> Settings:
    """Get settings (placeholder)."""
    raise RuntimeError("Dependency not initialized")


def get_ingestion_service() -> IngestionService:
    """Get ingestion service (placeholder)."""
    raise RuntimeError("Dependency not initialized")


@router.post("/api/init", response_model=InitResponse, tags=["initialization"])
async def initialize_index(
    settings: Settings = Depends(get_settings),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
) -> InitResponse:
    """Destroy existing collection and re-index source file.

    Args:
        settings: Application settings (dependency).
        ingestion_service: Ingestion service (dependency).

    Returns:
        Initialization response with statistics.

    Raises:
        HTTPException: If initialization fails.
    """
    try:
        logger.info("Starting initialization/reindexing")

        stats = await ingestion_service.ingest(
            source_file=settings.ingestion.source_file,
            embedding_dim=settings.llama.embedding_dim,
        )

        logger.info("Initialization complete: %s", stats)

        return InitResponse(
            status="success",
            message="Collection recreated and indexed successfully",
            statistics=stats,
        )

    except IngestionError as e:
        logger.error("Initialization failed: %s", e)
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "type": "ingestion_error",
                    "message": str(e),
                    "details": e.context,
                }
            },
        ) from e

    except Exception as e:
        logger.exception("Unexpected error during initialization")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "type": "internal_error",
                    "message": "Initialization failed unexpectedly",
                    "details": {"exception": str(e)},
                }
            },
        ) from e

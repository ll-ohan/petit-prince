import logging

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import settings

logger = logging.getLogger("gateway.models")
router: APIRouter = APIRouter()


@router.get("/models")
async def get_models() -> JSONResponse:
    """Retourne la liste des modèles disponibles depuis le LLM endpoint."""
    headers = (
        {"Authorization": f"Bearer {settings.llm_api_key}"}
        if settings.llm_api_key
        else {}
    )

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{settings.llm_base_url}/models", headers=headers
            )
            response.raise_for_status()
            return JSONResponse(content=response.json())
        except Exception as e:
            logger.warning(
                "Échec de la récupération des modèles depuis le backend LLM : %s", e
            )
            # Fallback en renvoyant le modèle configuré par défaut
            return JSONResponse(
                content={
                    "object": "list",
                    "data": [
                        {
                            "id": settings.llm_model,
                            "object": "model",
                            "owned_by": "local",
                        }
                    ],
                }
            )

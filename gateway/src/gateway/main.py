import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from prompts import PromptLoader

from .routers.chat import router as chat_router
from .routers.models import router as models_router
from .routers.responses import router as responses_router
from .routers.titrate import router as titrate_router
from .services import mcp_manager

logger = logging.getLogger("gateway")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gère l'initialisation et la fermeture des connexions globales."""
    logger.info("Connexion au serveur MCP...")
    try:
        await mcp_manager.connect()
        logger.info("Connecté au serveur MCP avec succès.")
        PromptLoader.load("prompts/prompts.yaml")
        logger.info("Registre de prompts chargé avec succès.")
    except Exception as e:
        logger.error(f"Impossible de se connecter au serveur MCP : {e}")
        raise  # Re-lancer l'exception pour empêcher le démarrage

    yield

    logger.info("Fermeture de la connexion MCP...")
    await mcp_manager.close()


app = FastAPI(title="API Gateway - Le Petit Prince RAG", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(chat_router)
app.include_router(models_router)
app.include_router(responses_router)
app.include_router(titrate_router)


@app.get("/health")
async def health() -> JSONResponse:
    """Endpoint de santé basique. Vérifie la connexion MCP."""
    mcp_connected = getattr(mcp_manager, "session", None) is not None
    status_code = 200 if mcp_connected else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if mcp_connected else "unhealthy",
            "mcp_connected": mcp_connected,
        },
    )

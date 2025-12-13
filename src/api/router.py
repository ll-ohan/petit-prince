"""Main API router."""

from fastapi import APIRouter

from src.api.routes import chat, init

router = APIRouter()

# Include route modules
router.include_router(init.router)
router.include_router(chat.router)

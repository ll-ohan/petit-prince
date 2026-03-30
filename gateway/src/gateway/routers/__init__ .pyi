"""Sous-package routers — endpoints FastAPI du gateway."""

from .chat import chat_completions
from .models import get_models
from .responses import create_response
from .titrate import generate_title

__all__ = ["chat_completions", "get_models", "create_response", "generate_title"]

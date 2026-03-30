from typing import Any

from pydantic import BaseModel, Field

from .. import settings


class ChatMessage(BaseModel):
    role: str
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ChatRequest(BaseModel):
    """Schéma compatible OpenAI pour la complétion."""

    model: str = Field(default_factory=lambda: settings.llm_model)
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None

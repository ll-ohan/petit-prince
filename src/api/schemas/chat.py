"""OpenAI-compatible chat schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Chat message."""

    role: Literal["system", "user", "assistant"] = Field(description="Message role")
    content: str = Field(min_length=1, description="Message content")


class ChatRequest(BaseModel):
    """Chat completion request (OpenAI-compatible)."""

    model: str = Field(default="petit-prince-rag", description="Model identifier")
    messages: list[Message] = Field(min_length=1, description="Conversation messages")
    stream: bool = Field(default=False, description="Enable streaming response")


class Usage(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatMessage(BaseModel):
    """Chat message in response."""

    role: str
    content: str


class Choice(BaseModel):
    """Chat completion choice."""

    index: int
    message: ChatMessage
    finish_reason: str


class ChatResponse(BaseModel):
    """Chat completion response (blocking)."""

    id: str
    object: str
    created: int
    model: str
    choices: list[Choice]
    usage: Usage
    x_metrics: dict | None = None

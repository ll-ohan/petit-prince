from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """Configuration de l'API Gateway."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "mistral-nemo:latest"
    llm_api_key: str | None = None
    llm_temperature: Annotated[float, Field(ge=0.0, le=2.0)] = 0.7

    mcp_server_url: str = "http://mcp_server:8001"
    mcp_sse_endpoint: str = "/sse"

    max_tool_iterations: Annotated[int, Field(ge=1, le=10)] = 8


settings = GatewaySettings()

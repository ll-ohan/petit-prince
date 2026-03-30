from pydantic import BaseModel

from .. import settings


class ResponsesRequest(BaseModel):
    """Schéma d'entrée pour l'API Responses."""

    model: str = settings.llm_model
    input: str
    stream: bool = False

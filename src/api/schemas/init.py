"""Init endpoint schemas."""

from pydantic import BaseModel


class InitResponse(BaseModel):
    """Initialization response."""

    status: str
    message: str
    statistics: dict

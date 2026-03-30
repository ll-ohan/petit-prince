from pydantic import BaseModel, Field


class TitrateRequest(BaseModel):
    """Schéma d'entrée pour la demande de titrage."""

    user_message: str = Field(
        ..., min_length=1, description="Premier message de l'utilisateur."
    )
    assistant_summary: str = Field(
        "",
        description="Optionnel: début ou résumé de la réponse de l'assistant pour affiner le titre.",
    )


class TitrateResponse(BaseModel):
    """Schéma de sortie contenant le titre généré."""

    title: str = Field(..., description="Le titre généré (3-6 mots).")

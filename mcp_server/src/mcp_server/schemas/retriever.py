from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

type NonEmptyStr = Annotated[
    str, StringConstraints(min_length=1, strip_whitespace=True)
]
type TopK = Annotated[
    int, Field(ge=1, le=10, description="Nombre d'extraits à retourner")
]


class RetrieverInput(BaseModel):
    """Schéma de validation pour l'entrée de l'outil Retriever."""

    query: NonEmptyStr = Field(description="La requête en langage naturel")
    top_k: TopK = 5
    chapter_filter: Annotated[
        int | None, Field(ge=1, le=27, description="Optionnel: filtrer par chapitre")
    ] = None


class RetrieverResultItem(BaseModel):
    """Un extrait retourné par Qdrant."""

    ref_id: int
    text: str
    chapter: int
    page: int
    score: float


class RetrieverOutput(BaseModel):
    """Format de sortie de l'outil Retriever."""

    results: list[RetrieverResultItem]
    query: str
    total: int

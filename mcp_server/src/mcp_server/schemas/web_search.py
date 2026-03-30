from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

type NonEmptyStr = Annotated[
    str, StringConstraints(min_length=1, strip_whitespace=True)
]


class WebSearchInput(BaseModel):
    """Schéma de validation pour l'outil Web Search."""

    query: NonEmptyStr = Field(description="La requête de recherche")
    site: Literal["monpetitprince.fr", "fr.wikipedia.org", "all"] = Field(
        default="all", description="Site cible ou 'all' pour les deux"
    )
    max_results: Annotated[int, Field(ge=1, le=5)] = 3


class WebSearchResultItem(BaseModel):
    """Un résultat de recherche web."""

    ref_id: int
    title: str
    url: str
    snippet: str
    source_domain: str


class WebSearchOutput(BaseModel):
    """Format de sortie de l'outil Web Search."""

    results: list[WebSearchResultItem]
    query: str
    total: int

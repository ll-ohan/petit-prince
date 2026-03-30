from typing import TypedDict

from embeddings.sparse import SparseVector
from qdrant_client import models

from .client import COLLECTION_NAME, client


class RetrievalResultDict(TypedDict):
    """Contrat de données pour un résultat de recherche."""

    ref_id: int
    text: str
    chapter: int
    page: int
    score: float


def search_passages(
    query_vector: SparseVector, top_k: int = 5, chapter_filter: int | None = None
) -> list[RetrievalResultDict]:
    """Recherche les extraits les plus pertinents dans la collection.

    Args:
        query_vector: Le vecteur sparse de la requête encodée par SPLADE.
        top_k: Nombre maximum d'extraits à retourner.
        chapter_filter: Optionnel, filtrer la recherche sur un chapitre précis.

    Returns:
        Une liste de dictionnaires typés contenant le texte et les métadonnées.
    """
    query_filter = None
    if chapter_filter is not None:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="chapter_id", match=models.MatchValue(value=chapter_filter)
                )
            ]
        )

    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=models.SparseVector(
            indices=query_vector.indices, values=query_vector.values
        ),
        using="splade",
        limit=top_k,
        query_filter=query_filter,
    )

    results: list[RetrievalResultDict] = []

    for i, hit in enumerate(response.points, start=1):
        payload = hit.payload or {}
        results.append(
            {
                "ref_id": i,
                "text": str(payload.get("text", "")),
                "chapter": int(payload.get("chapter_id", 0)),
                "page": int(payload.get("page_start", 0)),
                "score": float(hit.score),
            }
        )

    return results

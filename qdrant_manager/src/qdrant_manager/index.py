import uuid

from qdrant_client import models

from indexer import IndexedChunk

from .client import COLLECTION_NAME, client


def setup_collection(reset: bool = False) -> None:
    """Crée la collection Qdrant configurée pour les vecteurs sparse SPLADE.

    Désactive la configuration des vecteurs denses standards puisque nous
    n'utilisons que la recherche lexicale/sémantique étendue de SPLADE.

    Args:
        reset: Si True, supprime la collection existante avant de la recréer.
    """
    if reset and client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)

    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={},  # Strictement vide, pas de vecteurs denses
            sparse_vectors_config={
                "splade": models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=False)
                )
            },
        )


def upsert_chunks(indexed_chunks: list[IndexedChunk]) -> int:
    """Insère ou met à jour un lot de chunks encodés dans Qdrant.

    Args:
        indexed_chunks: Liste des chunks avec leurs vecteurs SPLADE.

    Returns:
        Le nombre de points insérés avec succès.
    """
    points: list[models.PointStruct] = []
    for ic in indexed_chunks:
        # Génération d'un UUID unique basé sur le hash du contenu
        # pour garantir l'idempotence des insertions
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, ic.chunk.content_hash))

        points.append(
            models.PointStruct(
                id=point_id,
                vector={
                    "splade": models.SparseVector(
                        indices=ic.vector.indices, values=ic.vector.values
                    )
                },
                payload={
                    "text": ic.chunk.text,
                    "chapter_id": ic.chunk.chapter_id,
                    "page_start": ic.chunk.page_start,
                    "page_end": ic.chunk.page_end,
                    "chunk_index": ic.chunk.chunk_index,
                    "source": ic.chunk.source,
                    "content_hash": ic.chunk.content_hash,
                },
            )
        )

    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)

    return len(points)

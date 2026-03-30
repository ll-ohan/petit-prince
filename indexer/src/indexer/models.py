import hashlib
from dataclasses import dataclass, field

from embeddings.sparse import SparseVector


@dataclass(slots=True, frozen=True)
class Chunk:
    """Représente un extrait de texte découpé avec ses métadonnées.

    Attributes:
        text: Le contenu textuel de l'extrait.
        chapter_id: Le numéro du chapitre d'où provient l'extrait.
        page_start: La page de début.
        page_end: La page de fin.
        chunk_index: L'index séquentiel du chunk dans le document.
        source: Le nom du document source.
        content_hash: Hash SHA-256 du contenu pour l'idempotence.
    """

    text: str
    chapter_id: int
    page_start: int
    page_end: int
    chunk_index: int
    source: str = "le_petit_prince"
    content_hash: str = field(init=False, compare=True)

    def __post_init__(self) -> None:
        """Génère automatiquement le hash du contenu après l'instanciation."""
        hash_val = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        object.__setattr__(self, "content_hash", f"sha256:{hash_val}")


@dataclass(slots=True)
class IndexedChunk:
    """Associe un chunk à sa représentation vectorielle sparse."""

    chunk: Chunk
    vector: SparseVector


@dataclass(slots=True)
class IndexingReport:
    """Rapport d'exécution du pipeline d'indexation."""

    total_chunks: int = 0
    indexed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list[str])

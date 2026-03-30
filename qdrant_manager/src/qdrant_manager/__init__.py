"""Package qdrant_manager — client et opérations Qdrant centralisés."""

from .client import COLLECTION_NAME, client
from .index import setup_collection, upsert_chunks
from .retrieve import RetrievalResultDict, search_passages

__all__ = [
    "client",
    "COLLECTION_NAME",
    "setup_collection",
    "upsert_chunks",
    "RetrievalResultDict",
    "search_passages",
]

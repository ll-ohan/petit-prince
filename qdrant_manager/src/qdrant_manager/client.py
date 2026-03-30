"""Gestionnaire centralisé pour la connexion et les opérations Qdrant."""

import os

from qdrant_client import QdrantClient

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "petit_prince")

client = QdrantClient(url=QDRANT_URL)

__all__ = ["client", "COLLECTION_NAME"]

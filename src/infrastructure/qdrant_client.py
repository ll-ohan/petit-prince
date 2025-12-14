"""Qdrant vector store client."""

import logging
import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.config.settings import QdrantConfig
from src.core.exceptions import VectorStoreError
from src.core.interfaces.vectorstore import SearchResult

logger = logging.getLogger(__name__)


class QdrantRepository:
    """Qdrant vector store implementation."""

    DISTANCE_MAP = {
        "Cosine": Distance.COSINE,
        "Euclid": Distance.EUCLID,
        "Dot": Distance.DOT,
    }

    def __init__(self, config: QdrantConfig):
        """Initialize Qdrant client.

        Args:
            config: Qdrant configuration.
        """
        self.config = config
        self.client = AsyncQdrantClient(host=config.host, port=config.port)
        self.collection_name = config.collection_name

    async def close(self) -> None:
        """Close Qdrant client."""
        await self.client.close()

    async def collection_exists(self) -> bool:
        """Check if collection exists.

        Returns:
            True if collection exists.
        """
        try:
            collections = await self.client.get_collections()
            return any(c.name == self.collection_name for c in collections.collections)
        except Exception as e:
            logger.warning("Failed to check collection existence: %s", e)
            return False

    async def create_collection(self, dimension: int) -> None:
        """Create or recreate collection.

        Args:
            dimension: Vector dimension.

        Raises:
            VectorStoreError: If creation fails.
        """
        try:
            # Delete if exists
            if await self.collection_exists():
                logger.info("Deleting existing collection: %s", self.collection_name)
                await self.client.delete_collection(self.collection_name)

            # Create new collection
            logger.info(
                "Creating collection: %s (dim=%d, distance=%s)",
                self.collection_name,
                dimension,
                self.config.distance,
            )

            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=self.DISTANCE_MAP[self.config.distance],
                ),
                on_disk_payload=self.config.on_disk_payload,
            )

            logger.info("Collection created successfully")

        except Exception as e:
            raise VectorStoreError(
                f"Failed to create collection: {e}",
                context={
                    "collection": self.collection_name,
                    "dimension": dimension,
                    "host": self.config.host,
                    "port": self.config.port,
                },
            ) from e

    async def upsert(self, texts: list[str], vectors: list[list[float]]) -> None:
        """Insert or update vectors.

        Args:
            texts: List of text chunks.
            vectors: Corresponding embedding vectors.

        Raises:
            VectorStoreError: If upsert fails.
        """
        if len(texts) != len(vectors):
            raise VectorStoreError(
                f"Text and vector count mismatch: {len(texts)} texts, {len(vectors)} vectors"
            )

        if not texts:
            return

        try:
            # Create points with UUIDs for idempotency
            points = []
            for text, vector in zip(texts, vectors):
                point_id = str(uuid.uuid4())
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={"text": text},
                    )
                )

            # Upsert in single batch
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

            logger.debug("Upserted %d points to collection", len(points))

        except Exception as e:
            raise VectorStoreError(
                f"Failed to upsert vectors: {e}",
                context={
                    "collection": self.collection_name,
                    "point_count": len(texts),
                },
            ) from e

    async def search(self, query_vector: list[float], top_k: int) -> list[SearchResult]:
        """Search for similar vectors.

        Args:
            query_vector: Query embedding.
            top_k: Number of results.

        Returns:
            List of search results.

        Raises:
            VectorStoreError: If search fails.
        """
        try:
            results = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k,
                with_payload=True,
            )

            search_results = []
            for hit in results.points:
                if hit.payload is None:
                    logger.warning("Result point has no payload, skipping")
                    continue
                search_results.append(
                    SearchResult(
                        text=hit.payload["text"],
                        score=hit.score,
                        metadata=hit.payload,
                    )
                )

            logger.debug("Search returned %d results", len(search_results))
            return search_results

        except Exception as e:
            raise VectorStoreError(
                f"Search failed: {e}",
                context={
                    "collection": self.collection_name,
                    "top_k": top_k,
                },
            ) from e

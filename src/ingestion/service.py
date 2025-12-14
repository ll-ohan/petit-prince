"""Ingestion service orchestrating the pipeline."""

import logging
from pathlib import Path

from src.core.interfaces.embedder import IEmbedder
from src.core.interfaces.vectorstore import IVectorStore
from src.ingestion.chunker import SentenceChunker
from src.ingestion.paragraph_builder import ParagraphBuilder
from src.ingestion.reader import TextReader
from src.utils.batch import batched

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrates text ingestion pipeline."""

    def __init__(
        self,
        embedder: IEmbedder,
        vectorstore: IVectorStore,
        sentences_per_paragraph: int,
        batch_size: int,
    ):
        """Initialize ingestion service.

        Args:
            embedder: Embedding service.
            vectorstore: Vector store service.
            sentences_per_paragraph: Sentences per paragraph chunk.
            batch_size: Batch size for embeddings.
        """
        self.embedder = embedder
        self.vectorstore = vectorstore
        self.batch_size = batch_size

        self.reader = TextReader()
        self.chunker = SentenceChunker(language="fr")
        self.paragraph_builder = ParagraphBuilder(sentences_per_paragraph)

    async def ingest(self, source_file: Path, embedding_dim: int) -> dict:
        """Execute full ingestion pipeline.

        Args:
            source_file: Path to source text file.
            embedding_dim: Embedding dimension for collection creation.

        Returns:
            Statistics dict with counts and timings.
        """
        logger.info("Starting ingestion from %s", source_file)

        # 1. Read file
        text = self.reader.read(source_file)

        # 2. Chunk into sentences
        sentences = self.chunker.chunk(text)
        logger.info("Extracted %d sentences", len(sentences))

        # 3. Build paragraphs
        paragraphs = self.paragraph_builder.build(sentences)
        logger.info("Built %d paragraphs", len(paragraphs))

        # 4. Recreate collection
        logger.info("Recreating vector collection (dimension=%d)", embedding_dim)
        await self.vectorstore.create_collection(embedding_dim)

        # 5. Embed paragraphs in batches
        logger.info(
            "Embedding %d paragraphs in batches of %d", len(paragraphs), self.batch_size
        )
        all_vectors = []

        for batch_idx, batch in enumerate(batched(paragraphs, self.batch_size)):
            logger.debug(
                "Embedding batch %d/%d (%d items)",
                batch_idx + 1,
                (len(paragraphs) + self.batch_size - 1) // self.batch_size,
                len(batch),
            )
            vectors = await self.embedder.embed_batch(batch)
            all_vectors.extend(vectors)

        logger.info("Generated %d embeddings", len(all_vectors))

        # 6. Upsert to vector store
        logger.info("Upserting %d vectors to collection", len(all_vectors))
        await self.vectorstore.upsert(paragraphs, all_vectors)

        logger.info("Ingestion complete: %d paragraphs indexed", len(paragraphs))

        return {
            "sentences": len(sentences),
            "paragraphs": len(paragraphs),
            "vectors": len(all_vectors),
        }

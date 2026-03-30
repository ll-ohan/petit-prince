"""Point d'entrée principal pour l'indexation du corpus Le Petit Prince."""

import argparse
import logging
import sys
from pathlib import Path

from embeddings.sparse import SpladeEncoder

from qdrant_manager import index as qdrant_index

from .models import IndexedChunk, IndexingReport
from .pipeline import TextChunker, load_source

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("indexer")


def run_pipeline(
    source_path: str, reset: bool = False, dry_run: bool = False, batch_size: int = 32
) -> IndexingReport:
    """Exécute le pipeline complet d'indexation.

    Args:
        source_path: Chemin vers le fichier texte source.
        reset: Si True, recrée la collection Qdrant de zéro.
        dry_run: Si True, effectue le traitement sans envoyer à Qdrant.
        batch_size: Taille des lots pour l'encodage et l'upsert.

    Returns:
        Un rapport détaillé de l'exécution.
    """
    report = IndexingReport()

    if not Path(source_path).exists():
        logger.error("Le fichier source %s n'existe pas.", source_path)
        report.errors.append("Fichier introuvable.")
        return report

    logger.info("Démarrage du pipeline d'indexation...")

    try:
        # 1. Chargement des pages brutes
        logger.info("Chargement et parsing de %s...", source_path)
        pages = load_source(source_path)
        logger.info("%d pages extraites.", len(pages))

        # 2. Initialisation de l'encodeur et du chunker
        logger.info("Initialisation du modèle SPLADE (ceci peut prendre un moment)...")
        encoder = SpladeEncoder(
            device="cpu"
        )  # Passer sur "cuda" ou "mps" via config en prod
        chunker = TextChunker(encoder=encoder, chunk_size=300, overlap=50)

        # 3. Découpage en chunks
        logger.info("Découpage du texte en chunks...")
        chunks = chunker.chunk_pages(pages)
        report.total_chunks = len(chunks)
        logger.info("%d chunks générés.", report.total_chunks)

        if dry_run:
            logger.info("[DRY RUN] Fin de la simulation. Aperçu du premier chunk :")
            if chunks:
                logger.info(chunks[0])
            return report

        # 4. Préparation de la base de données
        logger.info("Configuration de la collection Qdrant (reset=%s)...", reset)
        qdrant_index.setup_collection(reset=reset)

        # 5. Encodage et Upsert par batch
        logger.info(
            "Encodage SPLADE et insertion dans Qdrant (batch_size=%d)...", batch_size
        )

        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i : i + batch_size]
            texts = [c.text for c in batch_chunks]

            # Encodage du batch complet
            encoded_vectors = encoder.encode_batch(
                texts, batch_size=batch_size, is_query=False
            )

            # Assemblage des IndexedChunks
            indexed_batch: list[IndexedChunk] = []
            for chunk, vector in zip(batch_chunks, encoded_vectors, strict=True):
                indexed_batch.append(IndexedChunk(chunk=chunk, vector=vector))

            # Upsert dans Qdrant
            inserted_count = qdrant_index.upsert_chunks(indexed_batch)
            report.indexed += inserted_count

            logger.info(
                "Progression : %d/%d chunks traités.",
                min(i + batch_size, report.total_chunks),
                report.total_chunks,
            )

        logger.info("Pipeline terminé avec succès. %d chunks indexés.", report.indexed)

    except Exception as e:
        logger.exception("Une erreur critique est survenue durant l'indexation.")
        report.errors.append(str(e))

    return report


def main() -> None:
    """Parse les arguments de la ligne de commande et lance le script."""
    parser = argparse.ArgumentParser(
        description="Indexeur SPLADE pour Le Petit Prince."
    )
    parser.add_argument(
        "--source", type=str, required=True, help="Chemin vers le fichier texte source."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Recréer la collection Qdrant avant d'indexer.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simuler le processus sans modifier Qdrant.",
    )
    parser.add_argument(
        "--batch-size", type=int, default=32, help="Taille des batchs d'encodage."
    )

    args = parser.parse_args()

    report = run_pipeline(
        source_path=args.source,
        reset=args.reset,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
    )

    if report.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()

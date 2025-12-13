"""Sentence chunker using ML-based boundary detection."""

import logging
import re

import pysbd

from src.core.exceptions import IngestionError

logger = logging.getLogger(__name__)


class SentenceChunker:
    """ML-based sentence boundary detection with noise filtering."""

    # Patterns to filter out as non-sentences
    NOISE_PATTERNS = [
        re.compile(r"^Chapitre\s+[IVXLCDM]+\.?$", re.IGNORECASE),
        re.compile(r"^\d+\.?$"),
        re.compile(r"^[IVXLCDM]+\.?$"),
    ]

    def __init__(self, language: str = "fr"):
        """Initialize sentence segmenter.

        Args:
            language: Language code for segmentation.
        """
        self.segmenter = pysbd.Segmenter(language=language, clean=False)

    def chunk(self, text: str) -> list[str]:
        """Split text into sentences with noise filtering.

        Args:
            text: Input text to chunk.

        Returns:
            List of cleaned sentences.

        Raises:
            IngestionError: If text is empty or contains only noise.
        """
        if not text or not text.strip():
            return []

        # Segment into sentences
        raw_sentences = self.segmenter.segment(text)

        # Filter noise and clean
        sentences = []
        for sentence in raw_sentences:
            cleaned = sentence.strip()

            # Skip empty
            if not cleaned:
                continue

            # Skip noise patterns
            if any(pattern.match(cleaned) for pattern in self.NOISE_PATTERNS):
                logger.debug("Filtered noise: %s", cleaned[:50])
                continue

            # Warn about very long sentences (potential parsing issue)
            if len(cleaned) > 1000:
                logger.warning(
                    "Very long sentence detected (%d chars): %s...",
                    len(cleaned),
                    cleaned[:100],
                )

            sentences.append(cleaned)

        if not sentences:
            raise IngestionError(
                "No valid sentences extracted from source text (only noise found)",
                context={"raw_sentence_count": len(raw_sentences)},
            )

        logger.debug(
            "Chunked into %d sentences (filtered %d noise items)",
            len(sentences),
            len(raw_sentences) - len(sentences),
        )

        return sentences

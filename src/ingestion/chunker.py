"""Sentence chunker using ML-based boundary detection."""

import logging
import re

import pysbd  # type: ignore[import-untyped]

from src.core.exceptions import IngestionError

logger = logging.getLogger(__name__)


class SentenceChunker:
    """ML-based sentence boundary detection with noise filtering."""

    # Patterns to filter out as non-sentences
    # Note: These are applied to individual lines/segments before full text merging
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
        
        Strategy:
        1. Split by lines to identify and remove "structural noise" (headers, isolated numbers).
        2. Merge remaining lines to fix broken sentences (mixed newlines).
        3. Segment the merged text into proper sentences.

        Args:
            text: Input text to chunk.

        Returns:
            List of cleaned sentences.

        Raises:
            IngestionError: If text is empty or contains only noise.
        """
        if not text or not text.strip():
            return []

        # Step 1: Filter structural noise line by line
        lines = text.splitlines()
        cleaned_lines = []
        
        filtered_count = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
                
            # Check for noise patterns on the isolated line
            if any(pattern.match(stripped) for pattern in self.NOISE_PATTERNS):
                filtered_count += 1
                logger.debug("Filtered noise line: %s", stripped[:50])
                continue
                
            cleaned_lines.append(stripped)

        if not cleaned_lines and filtered_count > 0:
             raise IngestionError(
                "No valid text extracted from source (only noise found)",
                context={"original_line_count": len(lines)}
            )
        
        if not cleaned_lines:
            return []

        # Step 2: Merge text to handle sentences broken by newlines
        merged_text = " ".join(cleaned_lines)

        # Step 3: Segment into sentences
        raw_sentences = self.segmenter.segment(merged_text)

        # Step 4: Final cleanup
        sentences = []
        for sentence in raw_sentences:
            cleaned = sentence.strip()
            if cleaned:
                # Optional: Check very long sentences
                if len(cleaned) > 1000:
                    logger.warning(
                        "Very long sentence detected (%d chars): %s...",
                        len(cleaned),
                        cleaned[:100],
                    )
                sentences.append(cleaned)

        logger.debug(
            "Chunked into %d sentences (filtered %d noise lines)",
            len(sentences),
            filtered_count,
        )

        return sentences
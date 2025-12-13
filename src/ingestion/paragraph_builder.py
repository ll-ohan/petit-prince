"""Paragraph builder from sentences."""

import logging

logger = logging.getLogger(__name__)


class ParagraphBuilder:
    """Build paragraph chunks from sentences."""

    def __init__(self, sentences_per_paragraph: int = 10):
        """Initialize paragraph builder.

        Args:
            sentences_per_paragraph: Number of sentences per paragraph.
        """
        self.sentences_per_paragraph = sentences_per_paragraph

    def build(self, sentences: list[str]) -> list[str]:
        """Group sentences into paragraph chunks.

        Args:
            sentences: List of sentences.

        Returns:
            List of paragraph chunks.
        """
        if not sentences:
            return []

        paragraphs = []
        for i in range(0, len(sentences), self.sentences_per_paragraph):
            chunk = sentences[i : i + self.sentences_per_paragraph]
            paragraph = " ".join(chunk)
            paragraphs.append(paragraph)

        logger.debug(
            "Built %d paragraphs from %d sentences (%d sentences/paragraph)",
            len(paragraphs),
            len(sentences),
            self.sentences_per_paragraph,
        )

        return paragraphs

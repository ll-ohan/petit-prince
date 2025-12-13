"""Tests for SentenceChunker."""

import pytest

from src.core.exceptions import IngestionError
from src.ingestion.chunker import SentenceChunker


class TestSentenceChunker:
    """Test sentence chunking."""

    def test_chunk_normal_text(self):
        """Normal text is chunked into sentences."""
        chunker = SentenceChunker(language="fr")
        text = "Le petit prince habitait une planète. Il possédait trois volcans. Il avait aussi une rose."

        sentences = chunker.chunk(text)

        assert len(sentences) == 3
        assert "Le petit prince" in sentences[0]
        assert "trois volcans" in sentences[1]
        assert "une rose" in sentences[2]

    @pytest.mark.edge_case
    def test_empty_text(self):
        """Empty string returns empty list."""
        chunker = SentenceChunker(language="fr")

        assert chunker.chunk("") == []

    @pytest.mark.edge_case
    def test_whitespace_only(self):
        """Whitespace-only text returns empty list."""
        chunker = SentenceChunker(language="fr")

        assert chunker.chunk("   \n\t\n   ") == []

    @pytest.mark.edge_case
    def test_chapter_headers_filtered(self):
        """Chapter headers are not returned as sentences."""
        chunker = SentenceChunker(language="fr")
        text = "Chapitre I\n\nLe petit prince habitait une planète."

        sentences = chunker.chunk(text)

        assert "Chapitre I" not in sentences
        assert any("petit prince" in s for s in sentences)

    @pytest.mark.edge_case
    def test_roman_numerals_filtered(self):
        """Standalone roman numerals are filtered."""
        chunker = SentenceChunker(language="fr")
        text = "IV\n\nCette planète était habitée par un roi."

        sentences = chunker.chunk(text)

        assert "IV" not in sentences
        assert any("roi" in s for s in sentences)

    @pytest.mark.edge_case
    def test_paragraph_numbers_filtered(self):
        """Paragraph numbers like '1.' are filtered."""
        chunker = SentenceChunker(language="fr")
        text = "1.\n\nLe petit prince aimait sa rose."

        sentences = chunker.chunk(text)

        assert "1." not in sentences
        assert any("rose" in s for s in sentences)

    @pytest.mark.edge_case
    def test_noise_only_raises(self):
        """Text with only noise raises IngestionError."""
        chunker = SentenceChunker(language="fr")
        text = "Chapitre I\n\nII\n\nChapitre III\n\n4."

        with pytest.raises(IngestionError) as exc_info:
            chunker.chunk(text)

        assert "noise" in str(exc_info.value).lower()

    @pytest.mark.edge_case
    def test_ellipsis_handling(self):
        """Ellipsis doesn't create false sentence boundaries."""
        chunker = SentenceChunker(language="fr")
        text = "Il dit... puis il se tut."

        sentences = chunker.chunk(text)

        # Should be treated as one sentence
        assert len(sentences) == 1

    @pytest.mark.edge_case
    def test_quoted_dialogue(self):
        """Quoted dialogue is handled correctly."""
        chunker = SentenceChunker(language="fr")
        text = '"Dessine-moi un mouton!" dit le petit prince.'

        sentences = chunker.chunk(text)

        assert len(sentences) == 1
        assert "Dessine-moi" in sentences[0]

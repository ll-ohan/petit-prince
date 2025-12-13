"""Tests for ParagraphBuilder."""

import pytest

from src.ingestion.paragraph_builder import ParagraphBuilder


class TestParagraphBuilder:
    """Test paragraph building."""

    def test_build_normal_paragraphs(self):
        """Sentences are grouped into paragraphs."""
        builder = ParagraphBuilder(sentences_per_paragraph=3)
        sentences = ["Sentence 1.", "Sentence 2.", "Sentence 3.", "Sentence 4.", "Sentence 5."]

        paragraphs = builder.build(sentences)

        assert len(paragraphs) == 2
        assert paragraphs[0] == "Sentence 1. Sentence 2. Sentence 3."
        assert paragraphs[1] == "Sentence 4. Sentence 5."

    def test_build_exact_multiple(self):
        """Exact multiple of sentences_per_paragraph."""
        builder = ParagraphBuilder(sentences_per_paragraph=2)
        sentences = ["Sentence 1.", "Sentence 2.", "Sentence 3.", "Sentence 4."]

        paragraphs = builder.build(sentences)

        assert len(paragraphs) == 2
        assert paragraphs[0] == "Sentence 1. Sentence 2."
        assert paragraphs[1] == "Sentence 3. Sentence 4."

    @pytest.mark.edge_case
    def test_build_empty_list(self):
        """Empty sentence list returns empty paragraphs."""
        builder = ParagraphBuilder(sentences_per_paragraph=3)

        assert builder.build([]) == []

    @pytest.mark.edge_case
    def test_build_fewer_than_target(self):
        """Fewer sentences than target still creates paragraph."""
        builder = ParagraphBuilder(sentences_per_paragraph=10)
        sentences = ["Sentence 1.", "Sentence 2."]

        paragraphs = builder.build(sentences)

        assert len(paragraphs) == 1
        assert paragraphs[0] == "Sentence 1. Sentence 2."

    def test_build_single_sentence(self):
        """Single sentence creates single paragraph."""
        builder = ParagraphBuilder(sentences_per_paragraph=5)
        sentences = ["Only sentence."]

        paragraphs = builder.build(sentences)

        assert len(paragraphs) == 1
        assert paragraphs[0] == "Only sentence."

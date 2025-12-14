"""Unit tests for ParagraphBuilder."""

import pytest

from src.ingestion.paragraph_builder import ParagraphBuilder


@pytest.mark.unit
class TestParagraphBuilder:

    def test_build_paragraphs_exact_division(self):
        """Test splitting when sentence count matches chunk size."""
        builder = ParagraphBuilder(sentences_per_paragraph=2)
        sentences = ["S1.", "S2.", "S3.", "S4."]

        paragraphs = builder.build(sentences)

        assert len(paragraphs) == 2
        assert paragraphs[0] == "S1. S2."
        assert paragraphs[1] == "S3. S4."

    def test_build_paragraphs_with_remainder(self):
        """Test splitting with a remainder chunk."""
        builder = ParagraphBuilder(sentences_per_paragraph=3)
        sentences = ["S1", "S2", "S3", "S4"]

        paragraphs = builder.build(sentences)

        assert len(paragraphs) == 2
        assert paragraphs[0] == "S1 S2 S3"
        assert paragraphs[1] == "S4"

    def test_build_empty_input(self):
        """Test building from empty list."""
        builder = ParagraphBuilder()
        assert builder.build([]) == []

    def test_build_single_paragraph(self):
        """Test input smaller than chunk size."""
        builder = ParagraphBuilder(sentences_per_paragraph=10)
        sentences = ["Only one."]

        paragraphs = builder.build(sentences)

        assert len(paragraphs) == 1
        assert paragraphs[0] == "Only one."

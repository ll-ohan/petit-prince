"""Tests for TextReader."""

from pathlib import Path

import pytest

from src.core.exceptions import IngestionError
from src.ingestion.reader import TextReader


class TestTextReader:
    """Test text file reading."""

    def test_read_valid_file(self):
        """Successfully read valid UTF-8 file."""
        reader = TextReader()
        content = reader.read(Path("tests/fixtures/sample_book.txt"))

        assert content
        assert "Petit Prince" in content
        assert len(content) > 0

    @pytest.mark.edge_case
    def test_read_empty_file(self):
        """Empty file raises IngestionError."""
        reader = TextReader()

        with pytest.raises(IngestionError) as exc_info:
            reader.read(Path("tests/fixtures/empty_file.txt"))

        assert "empty" in str(exc_info.value).lower()

    @pytest.mark.edge_case
    def test_read_nonexistent_file(self):
        """Non-existent file raises IngestionError."""
        reader = TextReader()

        with pytest.raises(IngestionError) as exc_info:
            reader.read(Path("/non/existent/file.txt"))

        assert "exist" in str(exc_info.value).lower()

    @pytest.mark.edge_case
    def test_read_whitespace_only_file(self, tmp_path):
        """File with only whitespace raises IngestionError."""
        file_path = tmp_path / "whitespace.txt"
        file_path.write_text("   \n\t\n   ")

        reader = TextReader()

        with pytest.raises(IngestionError) as exc_info:
            reader.read(file_path)

        assert "empty" in str(exc_info.value).lower()

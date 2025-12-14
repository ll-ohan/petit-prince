"""
Unit tests for TextReader - file reading with encoding detection.

Tests reading text files with various encodings, handling empty files,
missing files, and encoding fallback behavior.
"""

from pathlib import Path

import pytest

from src.core.exceptions import IngestionError
from src.ingestion.reader import TextReader


@pytest.mark.unit
class TestTextReaderNominalCases:
    """Test TextReader with valid inputs."""

    def test_read_utf8_file(self, sample_text_file: Path):
        """Test reading a standard UTF-8 encoded file."""
        reader = TextReader()
        content = reader.read(sample_text_file)

        assert isinstance(content, str)
        assert len(content) > 0
        assert "Petit Prince" in content
        assert "renard" in content

    def test_read_returns_full_content(self, sample_text_file: Path):
        """Test that read() returns complete file content."""
        reader = TextReader()
        content = reader.read(sample_text_file)

        # Verify against direct read
        expected = sample_text_file.read_text(encoding="utf-8")
        assert content == expected

    def test_read_preserves_whitespace(self, temp_dir: Path):
        """Test that whitespace and newlines are preserved."""
        content_with_whitespace = "Line 1\n\nLine 2\n  Indented\n"
        file_path = temp_dir / "whitespace.txt"
        file_path.write_text(content_with_whitespace, encoding="utf-8")

        reader = TextReader()
        result = reader.read(file_path)

        assert result == content_with_whitespace

    def test_read_french_accents(self, temp_dir: Path):
        """Test reading French text with accented characters."""
        french_text = "Le Petit Prince habitait une planète très éloignée. Il était très attaché à sa rose."
        file_path = temp_dir / "french.txt"
        file_path.write_text(french_text, encoding="utf-8")

        reader = TextReader()
        result = reader.read(file_path)

        assert result == french_text
        assert "très" in result
        assert "éloignée" in result


@pytest.mark.unit
@pytest.mark.edge_case
class TestTextReaderEncodingFallback:
    """Test TextReader encoding detection and fallback."""

    def test_read_latin1_file(self, invalid_encoding_file: Path):
        """Test reading file with Latin-1 encoding (fallback)."""
        reader = TextReader()
        content = reader.read(invalid_encoding_file)

        assert isinstance(content, str)
        assert "caractères" in content or "caractres" in content
        # Exact match depends on encoding interpretation

    def test_read_utf8_sig_bom(self, temp_dir: Path):
        """Test reading UTF-8 file with BOM (Byte Order Mark)."""
        text = "Le Petit Prince"
        file_path = temp_dir / "utf8_bom.txt"
        file_path.write_text(text, encoding="utf-8-sig")

        reader = TextReader()
        content = reader.read(file_path)

        # BOM should be handled transparently
        assert content.strip() == text

    def test_read_cp1252_file(self, temp_dir: Path):
        """Test reading Windows CP1252 encoded file."""
        text = "Texte avec guillemets « français »"
        file_path = temp_dir / "cp1252.txt"
        file_path.write_bytes(text.encode("cp1252"))

        reader = TextReader()
        content = reader.read(file_path)

        assert isinstance(content, str)
        assert len(content) > 0


@pytest.mark.unit
@pytest.mark.edge_case
class TestTextReaderErrorHandling:
    """Test TextReader error conditions."""

    def test_read_nonexistent_file(self, temp_dir: Path):
        """Test that reading nonexistent file raises IngestionError."""
        nonexistent = temp_dir / "does_not_exist.txt"
        reader = TextReader()

        with pytest.raises(IngestionError) as exc_info:
            reader.read(nonexistent)

        error = exc_info.value
        assert "does not exist" in str(error)
        assert str(nonexistent) in str(error)
        assert error.context["file_path"] == str(nonexistent)

    def test_read_empty_file(self, empty_file: Path):
        """Test that reading empty file raises IngestionError."""
        reader = TextReader()

        with pytest.raises(IngestionError) as exc_info:
            reader.read(empty_file)

        error = exc_info.value
        assert "empty" in str(error).lower()
        assert error.context["file_path"] == str(empty_file)

    def test_read_whitespace_only_file(self, whitespace_only_file: Path):
        """Test that file with only whitespace raises IngestionError."""
        reader = TextReader()

        with pytest.raises(IngestionError) as exc_info:
            reader.read(whitespace_only_file)

        error = exc_info.value
        assert "empty" in str(error).lower()

    def test_read_binary_file_fails_gracefully(self, temp_dir: Path):
        """Test that reading binary file raises IngestionError with context."""
        binary_file = temp_dir / "binary.bin"
        binary_file.write_bytes(bytes([0xFF, 0xFE, 0x00, 0x01, 0x80, 0x90]))

        reader = TextReader()

        with pytest.raises(IngestionError) as exc_info:
            reader.read(binary_file)

        error = exc_info.value
        assert "Could not decode" in str(error)
        assert "tried_encodings" in error.context


@pytest.mark.unit
class TestTextReaderLogging:
    """Test TextReader logging behavior."""

    def test_read_logs_success(self, sample_text_file: Path, caplog):
        """Test that successful read is logged."""
        reader = TextReader()

        with caplog.at_level("INFO"):
            content = reader.read(sample_text_file)

        assert "Read" in caplog.text
        assert str(sample_text_file) in caplog.text
        assert "utf-8" in caplog.text.lower()

    def test_read_warns_on_fallback_encoding(self, invalid_encoding_file: Path, caplog):
        """Test that fallback encoding triggers warning."""
        reader = TextReader()

        with caplog.at_level("WARNING"):
            content = reader.read(invalid_encoding_file)

        # Should warn when using non-UTF-8 encoding
        assert "fallback" in caplog.text.lower() or "latin" in caplog.text.lower()


@pytest.mark.unit
class TestTextReaderEdgeCases:
    """Test edge cases and special scenarios."""

    def test_read_very_large_file(self, large_text_corpus: Path):
        """Test reading a large file (1MB+)."""
        reader = TextReader()
        content = reader.read(large_text_corpus)

        assert len(content) > 1_000_000  # At least 1MB
        assert isinstance(content, str)

    def test_read_single_character_file(self, temp_dir: Path):
        """Test reading file with single character."""
        file_path = temp_dir / "single.txt"
        file_path.write_text("A", encoding="utf-8")

        reader = TextReader()
        content = reader.read(file_path)

        assert content == "A"

    def test_read_unicode_emoji_file(self, temp_dir: Path):
        """Test reading file containing Unicode emoji."""
        text = "Le Petit Prince 🌟 et sa rose 🌹"
        file_path = temp_dir / "emoji.txt"
        file_path.write_text(text, encoding="utf-8")

        reader = TextReader()
        content = reader.read(file_path)

        assert content == text
        assert "🌟" in content
        assert "🌹" in content

    def test_read_multiple_times_same_file(self, sample_text_file: Path):
        """Test that reading same file multiple times is consistent."""
        reader = TextReader()

        content1 = reader.read(sample_text_file)
        content2 = reader.read(sample_text_file)
        content3 = reader.read(sample_text_file)

        assert content1 == content2 == content3

    def test_reader_instance_can_read_multiple_files(
        self, sample_text_file: Path, temp_dir: Path
    ):
        """Test that single TextReader instance can read multiple files."""
        reader = TextReader()

        # Create second file
        file2 = temp_dir / "second.txt"
        file2.write_text("Another text", encoding="utf-8")

        content1 = reader.read(sample_text_file)
        content2 = reader.read(file2)

        assert content1 != content2
        assert "Petit Prince" in content1
        assert "Another text" in content2

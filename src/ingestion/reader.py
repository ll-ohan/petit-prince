"""Text file reader with encoding detection."""

import logging
from pathlib import Path

from src.core.exceptions import IngestionError

logger = logging.getLogger(__name__)


class TextReader:
    """Read text files with encoding fallback."""

    ENCODINGS = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    def read(self, file_path: Path) -> str:
        """Read text file with automatic encoding detection.

        Args:
            file_path: Path to text file.

        Returns:
            File content as string.

        Raises:
            IngestionError: If file cannot be read or is empty.
        """
        if not file_path.exists():
            raise IngestionError(
                f"Source file does not exist: {file_path}",
                context={"file_path": str(file_path)},
            )

        content = None
        used_encoding = None

        for encoding in self.ENCODINGS:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                used_encoding = encoding
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            raise IngestionError(
                f"Could not decode file with any supported encoding: {self.ENCODINGS}",
                context={"file_path": str(file_path), "tried_encodings": self.ENCODINGS},
            )

        if not content.strip():
            raise IngestionError(
                f"Source file is empty: {file_path}",
                context={"file_path": str(file_path)},
            )

        if used_encoding != "utf-8":
            logger.warning(
                "File %s read with fallback encoding: %s (not UTF-8)", file_path, used_encoding
            )

        logger.info(
            "Read %d characters from %s (encoding: %s)",
            len(content),
            file_path,
            used_encoding,
        )

        return content

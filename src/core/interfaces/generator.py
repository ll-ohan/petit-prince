"""Generator interface for text generation."""

from collections.abc import AsyncIterator
from typing import Any, Protocol


class IGenerator(Protocol):
    """Protocol for text generation services."""

    async def generate(self, messages: list[dict[Any, Any]]) -> str:
        """Generate response from messages (blocking).

        Args:
            messages: List of message dicts with 'role' and 'content'.

        Returns:
            Generated response text.

        Raises:
            GenerationError: If generation fails.
        """
        ...

    def generate_stream(self, messages: list[dict[Any, Any]]) -> AsyncIterator[str]:
        """Generate response from messages (streaming).

        Args:
            messages: List of message dicts with 'role' and 'content'.

        Yields:
            Generated text chunks.

        Raises:
            GenerationError: If generation fails.
        """
        ...

    async def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to tokenize.

        Returns:
            Token count.

        Raises:
            GenerationError: If tokenization fails.
        """
        ...

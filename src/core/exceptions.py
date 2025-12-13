"""Custom exceptions hierarchy for Le Petit Prince RAG."""


class PetitPrinceError(Exception):
    """Base exception with context preservation."""

    def __init__(self, message: str, context: dict | None = None):
        """Initialize exception with message and optional context.

        Args:
            message: Error message.
            context: Additional context information for debugging.
        """
        self.context = context or {}
        super().__init__(message)

    def __str__(self) -> str:
        """Return formatted error message with context."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{super().__str__()} [{context_str}]"
        return super().__str__()


class ConfigurationError(PetitPrinceError):
    """Configuration validation or loading error."""


class IngestionError(PetitPrinceError):
    """Error during text ingestion or processing."""


class EmbeddingError(PetitPrinceError):
    """Error during embedding generation."""


class RetrievalError(PetitPrinceError):
    """Error during vector search or retrieval."""


class RerankError(PetitPrinceError):
    """Error during document reranking."""


class GenerationError(PetitPrinceError):
    """Error during text generation."""


class VectorStoreError(PetitPrinceError):
    """Error during vector store operations."""

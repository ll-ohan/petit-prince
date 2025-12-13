"""Batch processing utilities."""

from typing import TypeVar

T = TypeVar("T")


def batched(items: list[T], batch_size: int) -> list[list[T]]:
    """Split list into batches.

    Args:
        items: List to batch.
        batch_size: Size of each batch.

    Returns:
        List of batches.
    """
    if batch_size <= 0:
        raise ValueError(f"batch_size must be > 0, got {batch_size}")

    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]

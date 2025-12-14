"""
Unit tests for batch processing utilities.

Tests the batched() function for correct splitting of lists into batches,
including edge cases like empty lists, remainders, and invalid batch sizes.
"""

import pytest

from src.utils.batch import batched


@pytest.mark.unit
class TestBatchedNominalCases:
    """Test batched() function with nominal inputs."""

    def test_batched_exact_division(self):
        """Test batching with list size exactly divisible by batch size."""
        items = list(range(10))
        batches = batched(items, batch_size=2)

        assert len(batches) == 5
        assert batches[0] == [0, 1]
        assert batches[1] == [2, 3]
        assert batches[4] == [8, 9]

    def test_batched_with_remainder(self):
        """Test batching with remainder (list size not divisible by batch size)."""
        items = list(range(10))
        batches = batched(items, batch_size=3)

        assert len(batches) == 4
        assert batches[0] == [0, 1, 2]
        assert batches[1] == [3, 4, 5]
        assert batches[2] == [6, 7, 8]
        assert batches[3] == [9]  # Remainder

    def test_batched_single_item_batches(self):
        """Test creating batches of size 1."""
        items = ["a", "b", "c"]
        batches = batched(items, batch_size=1)

        assert len(batches) == 3
        assert batches == [["a"], ["b"], ["c"]]

    def test_batched_preserves_order(self):
        """Test that batching preserves item order."""
        items = [10, 20, 30, 40, 50]
        batches = batched(items, batch_size=2)

        flattened = [item for batch in batches for item in batch]
        assert flattened == items

    def test_batched_with_strings(self):
        """Test batching with string items."""
        items = ["Le", "Petit", "Prince", "habitait", "une", "planète"]
        batches = batched(items, batch_size=2)

        assert len(batches) == 3
        assert batches[0] == ["Le", "Petit"]
        assert batches[2] == ["une", "planète"]

    def test_batched_with_mixed_types(self):
        """Test batching with mixed type items."""
        items = [1, "two", 3.0, None, True]
        batches = batched(items, batch_size=2)

        assert len(batches) == 3
        assert batches[0] == [1, "two"]
        assert batches[1] == [3.0, None]
        assert batches[2] == [True]


@pytest.mark.unit
@pytest.mark.edge_case
class TestBatchedEdgeCases:
    """Test batched() function with edge cases and boundary conditions."""

    def test_batched_empty_list(self):
        """Test batching an empty list returns empty list."""
        batches = batched([], batch_size=5)

        assert batches == []
        assert isinstance(batches, list)

    def test_batched_size_larger_than_list(self):
        """Test batch size larger than list length returns single batch."""
        items = [1, 2, 3]
        batches = batched(items, batch_size=10)

        assert len(batches) == 1
        assert batches[0] == items

    def test_batched_size_equals_list_length(self):
        """Test batch size equal to list length returns single batch."""
        items = list(range(5))
        batches = batched(items, batch_size=5)

        assert len(batches) == 1
        assert batches[0] == items

    def test_batched_large_list(self):
        """Test batching a large list (performance check)."""
        items = list(range(10000))
        batches = batched(items, batch_size=100)

        assert len(batches) == 100
        assert len(batches[0]) == 100
        assert len(batches[-1]) == 100

        # Verify total count preserved
        total_items = sum(len(batch) for batch in batches)
        assert total_items == 10000

    def test_batched_single_item_list(self):
        """Test batching a list with single item."""
        items = [42]
        batches = batched(items, batch_size=1)

        assert len(batches) == 1
        assert batches[0] == [42]

    def test_batched_preserves_item_identity(self):
        """Test that batching preserves object identity (not copying)."""

        class CustomObject:
            def __init__(self, value: int):
                self.value = value

        obj1 = CustomObject(1)
        obj2 = CustomObject(2)
        items = [obj1, obj2]

        batches = batched(items, batch_size=1)

        # Check that objects are same instances, not copies
        assert batches[0][0] is obj1
        assert batches[1][0] is obj2


@pytest.mark.unit
@pytest.mark.edge_case
class TestBatchedErrorHandling:
    """Test batched() function error handling."""

    def test_batched_zero_batch_size(self):
        """Test that batch_size=0 raises ValueError."""
        items = [1, 2, 3]

        with pytest.raises(ValueError) as exc_info:
            batched(items, batch_size=0)

        error_msg = str(exc_info.value)
        assert "batch_size must be > 0" in error_msg
        assert "got 0" in error_msg

    def test_batched_negative_batch_size(self):
        """Test that negative batch_size raises ValueError."""
        items = [1, 2, 3]

        with pytest.raises(ValueError) as exc_info:
            batched(items, batch_size=-5)

        error_msg = str(exc_info.value)
        assert "batch_size must be > 0" in error_msg
        assert "got -5" in error_msg

    @pytest.mark.parametrize("invalid_size", [0, -1, -10, -100])
    def test_batched_various_invalid_sizes(self, invalid_size: int):
        """Test various invalid batch sizes raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            batched([1, 2, 3], batch_size=invalid_size)

        assert "batch_size must be > 0" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.performance
class TestBatchedPerformance:
    """Test batched() function performance characteristics."""

    def test_batched_performance_benchmark(self, benchmark):
        """Benchmark batched() performance with moderate size list."""
        items = list(range(1000))

        result = benchmark(batched, items, 10)

        # Verify correctness alongside performance
        assert len(result) == 100
        assert all(len(batch) == 10 for batch in result)

    def test_batched_memory_efficiency(self):
        """Test that batched() doesn't create unnecessary copies."""

        # Create list with known objects
        items = [object() for _ in range(100)]
        original_ids = [id(item) for item in items]

        batches = batched(items, batch_size=10)

        # Verify same objects (by id) in batches
        batched_ids = [id(item) for batch in batches for item in batch]
        assert batched_ids == original_ids


@pytest.mark.unit
class TestBatchedTypeHints:
    """Test that batched() maintains proper typing."""

    def test_batched_generic_typing_integers(self):
        """Test type preservation with integers."""
        items: list[int] = [1, 2, 3, 4, 5]
        batches: list[list[int]] = batched(items, batch_size=2)

        # Runtime check - all items should be ints
        for batch in batches:
            for item in batch:
                assert isinstance(item, int)

    def test_batched_generic_typing_strings(self):
        """Test type preservation with strings."""
        items: list[str] = ["a", "b", "c"]
        batches: list[list[str]] = batched(items, batch_size=2)

        for batch in batches:
            for item in batch:
                assert isinstance(item, str)

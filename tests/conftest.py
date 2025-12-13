"""Pytest configuration and shared fixtures."""

import pytest


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "edge_case: marks test as edge case scenario")
    config.addinivalue_line("markers", "integration: marks test as integration test")

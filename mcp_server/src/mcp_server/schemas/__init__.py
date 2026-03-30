"""Sous-package schemas — schémas Pydantic des outils MCP."""

from .retriever import RetrieverInput, RetrieverOutput, RetrieverResultItem
from .web_search import WebSearchInput, WebSearchOutput, WebSearchResultItem

__all__ = [
    "RetrieverInput",
    "RetrieverOutput",
    "RetrieverResultItem",
    "WebSearchInput",
    "WebSearchResultItem",
    "WebSearchOutput",
]

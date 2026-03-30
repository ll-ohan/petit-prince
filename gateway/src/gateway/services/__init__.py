"""Sous-package services — logique métier et clients externes du gateway."""

from .mcp_client import MCPConnectionManager, mcp_manager
from .tool_loop import format_mcp_tools_for_openai, stream_chat_loop

__all__ = [
    "MCPConnectionManager",
    "mcp_manager",
    "format_mcp_tools_for_openai",
    "stream_chat_loop",
]

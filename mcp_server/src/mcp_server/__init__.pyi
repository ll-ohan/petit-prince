"""Package mcp_server — serveur MCP (SSE) pour Le Petit Prince."""

from .config import MCPSettings, settings
from .main import (
    EmptyResponse,
    call_tool,
    list_tools,
)
from .main import (
    app as mcp_api_app,
)
from .main import (
    mcp as mcp_server_app,
)
from .main import (
    sse_transport as mcp_sse_transprot,
)

__all__ = [
    "MCPSettings",
    "settings",
    "mcp_server_app",
    "list_tools",
    "call_tool",
    "mcp_api_app",
    "mcp_sse_transprot",
    "EmptyResponse",
]

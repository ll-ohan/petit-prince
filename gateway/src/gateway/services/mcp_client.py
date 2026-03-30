from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client

from .. import settings


class MCPConnectionManager:
    """Gère la connexion persistante au serveur MCP via SSE."""

    def __init__(self) -> None:
        self.session: ClientSession | None = None
        self._exit_stack = AsyncExitStack()

    async def connect(self) -> None:
        """Établit la connexion SSE avec le serveur MCP."""
        url = f"{settings.mcp_server_url}{settings.mcp_sse_endpoint}"

        # Le client SSE du SDK MCP est un context manager asynchrone
        sse_ctx = sse_client(url)
        streams = await self._exit_stack.enter_async_context(sse_ctx)

        # Initialisation de la session sur ces streams
        self.session = await self._exit_stack.enter_async_context(
            ClientSession(streams[0], streams[1])
        )
        await self.session.initialize()

    async def close(self) -> None:
        """Ferme proprement la connexion."""
        await self._exit_stack.aclose()
        self.session = None


# Instance globale pour l'application
mcp_manager = MCPConnectionManager()

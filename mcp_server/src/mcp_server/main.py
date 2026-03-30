import traceback

import mcp.types as types
from embeddings.sparse import SpladeEncoder
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from .schemas import RetrieverInput, WebSearchInput
from .tools import RetrieverTool, WebSearchTool

encoder = SpladeEncoder(device="cpu")
retriever_tool = RetrieverTool(encoder=encoder)
web_search_tool = WebSearchTool()

mcp = Server("petit-prince-mcp")


@mcp.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
async def list_tools() -> list[types.Tool]:
    """Expose la définition des outils disponibles au client MCP (l'Orchestrateur)."""
    return [
        types.Tool(
            name="retriever",
            description=(
                "Recherche des passages du Petit Prince par mots-clés (vecteur sparse SPLADE). "
                "Formule la requête comme une liste de termes précis et significatifs extraits "
                "de la question (noms de personnages, objets, thèmes, verbes d'action) — "
                "pas une phrase complète. "
                "Utilise chapter_filter pour restreindre la recherche à un chapitre spécifique "
                "si la question le mentionne explicitement. "
                "Appelle cet outil en premier, avant toute recherche web, "
                "et plusieurs fois avec des requêtes différentes si la question est large."
            ),
            inputSchema=RetrieverInput.model_json_schema(),
        ),
        types.Tool(
            name="web_search",
            description=(
                "Recherche des informations sur Le Petit Prince sur deux sources autorisées : "
                "monpetitprince.fr (site officiel, analyses, contexte éditorial) "
                "et fr.wikipedia.org (biographie de Saint-Exupéry, contexte historique, réception). "
                "Utilise cet outil uniquement si le retriever ne fournit pas d'éléments suffisants, "
                "ou si la question porte sur des informations absentes du texte "
                "(biographie, adaptations, traductions, récompenses). "
                "Formule la requête en français avec des termes ciblés."
            ),
            inputSchema=WebSearchInput.model_json_schema(),
        ),
    ]


@mcp.call_tool()  # type: ignore[untyped-decorator]
async def call_tool(name: str, arguments: dict[str, object]) -> list[types.TextContent]:
    """Route l'exécution de l'outil demandé par le LLM."""
    if name == "retriever":
        retriever_params = RetrieverInput.model_validate(arguments)
        retriever_result = await retriever_tool.execute(retriever_params)
        return [types.TextContent(type="text", text=retriever_result.model_dump_json())]

    elif name == "web_search":
        websearch_params = WebSearchInput.model_validate(arguments)
        websearch_result = await web_search_tool.execute(websearch_params)
        return [types.TextContent(type="text", text=websearch_result.model_dump_json())]

    raise ValueError(f"Outil non supporté : {name}")


app = FastAPI(title="MCP Server - Le Petit Prince")
sse_transport = SseServerTransport("/messages")


class EmptyResponse(Response):
    """Modèle de réponse vide pour les endpoints FastAPI."""

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        pass


@app.get("/sse")
async def handle_sse(request: Request) -> Response:
    """Établit la connexion SSE (keep-alive) avec l'orchestrateur."""
    try:
        async with sse_transport.connect_sse(
            request.scope,
            request.receive,
            request._send,  # pyright: ignore[reportPrivateUsage]
        ) as (
            read_stream,
            write_stream,
        ):
            await mcp.run(
                read_stream, write_stream, mcp.create_initialization_options()
            )
    except Exception as e:
        print(f"⚠️ Erreur MCP : {e}")
        traceback.print_exc()

    return EmptyResponse()


@app.post("/messages")
@app.options("/messages")
async def handle_messages(request: Request) -> Response:
    """Reçoit les messages de l'orchestrateur."""
    await sse_transport.handle_post_message(
        request.scope,
        request.receive,
        request._send,  # pyright: ignore[reportPrivateUsage]
    )
    return EmptyResponse()


@app.get("/health")
async def health() -> JSONResponse:
    """Vérifie la santé des dépendances externes (ex: Qdrant).

    Retourne 200 si Qdrant est joignable, 503 sinon.
    """
    try:
        from qdrant_manager import client

        client.get_collections()
        qdrant_ok = True
    except Exception:
        qdrant_ok = False

    status_code = 200 if qdrant_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if qdrant_ok else "unhealthy", "qdrant": qdrant_ok},
    )

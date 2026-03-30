from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..schemas import ChatRequest
from ..services import stream_chat_loop

router: APIRouter = APIRouter()


@router.post("/chat/completions")
async def chat_completions(request: ChatRequest) -> StreamingResponse:
    """Endpoint principal compatible avec l'API OpenAI Chat Completions."""

    return StreamingResponse(stream_chat_loop(request), media_type="text/event-stream")

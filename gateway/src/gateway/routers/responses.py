from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..schemas import ChatMessage, ChatRequest, ResponsesRequest
from ..services import stream_chat_loop

router: APIRouter = APIRouter()


@router.post("/responses")
async def create_response(request: ResponsesRequest) -> StreamingResponse:
    """Endpoint alternatif compatible avec l'API Responses d'OpenAI."""

    # Wrapping de l'input en un ChatRequest standard
    chat_request = ChatRequest(
        model=request.model,
        messages=[ChatMessage(role="user", content=request.input)],
        stream=request.stream,
    )

    return StreamingResponse(
        stream_chat_loop(chat_request), media_type="text/event-stream"
    )

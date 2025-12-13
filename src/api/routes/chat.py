"""Chat endpoint for RAG queries."""

import logging
import time

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse

from src.api.schemas.chat import ChatRequest
from src.core.exceptions import GenerationError, RetrievalError
from src.generation.response_handler import RequestMetrics, ResponseHandler
from src.generation.service import GenerationService
from src.infrastructure.llama_client import LlamaClient

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/v1/chat/completions", tags=["chat"])
async def chat_completion(
    request: ChatRequest,
    generation_service: GenerationService = Depends(),
    llama_client: LlamaClient = Depends(),
    x_include_metrics: str | None = Header(None),
):
    """OpenAI-compatible chat completion endpoint.

    Args:
        request: Chat request.
        generation_service: Generation service (dependency).
        llama_client: Llama client (dependency).
        x_include_metrics: Optional header to include extended metrics.

    Returns:
        Chat completion response (streaming or blocking).

    Raises:
        HTTPException: If generation fails.
    """
    include_extended = x_include_metrics and x_include_metrics.lower() == "true"
    metrics = RequestMetrics()
    response_handler = ResponseHandler()

    try:
        # Validate messages
        if not request.messages:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": {
                        "type": "validation_error",
                        "message": "Messages array cannot be empty",
                    }
                },
            )

        # Convert to dict format
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        # Process query through RAG pipeline
        final_messages, reranked_docs = await generation_service.process_query(messages, metrics)

        # Generate response
        if request.stream:
            # Streaming response
            start = time.perf_counter()

            async def generate_with_metrics():
                nonlocal metrics
                chunk_count = 0

                async for chunk in llama_client.generate_stream(final_messages):
                    chunk_count += len(chunk)
                    yield chunk

                # Estimate completion tokens
                metrics.completion_tokens = chunk_count // 4
                metrics.generation_ms = (time.perf_counter() - start) * 1000

            content_stream = generate_with_metrics()

            # Wrap in SSE format
            async def sse_stream():
                async for sse_chunk in response_handler.format_streaming_completion(
                    content_stream, metrics, include_extended
                ):
                    yield sse_chunk

            return StreamingResponse(sse_stream(), media_type="text/event-stream")

        else:
            # Blocking response
            start = time.perf_counter()
            content = await llama_client.generate(final_messages)
            metrics.generation_ms = (time.perf_counter() - start) * 1000

            # Count completion tokens
            try:
                metrics.completion_tokens = await llama_client.count_tokens(content)
            except GenerationError:
                logger.warning("Token counting failed for completion, using estimate")
                metrics.completion_tokens = len(content) // 4

            return response_handler.format_completion(content, metrics, include_extended)

    except RetrievalError as e:
        logger.error("Retrieval failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "type": "retrieval_error",
                    "message": str(e),
                    "details": e.context,
                }
            },
        ) from e

    except GenerationError as e:
        logger.error("Generation failed: %s", e)
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "type": "generation_error",
                    "message": str(e),
                    "details": e.context,
                }
            },
        ) from e

    except Exception as e:
        logger.exception("Unexpected error during chat completion")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "type": "internal_error",
                    "message": "Chat completion failed unexpectedly",
                    "details": {"exception": str(e)},
                }
            },
        ) from e

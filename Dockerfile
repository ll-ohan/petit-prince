FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml ./
COPY uv.lock ./

COPY pyproject.toml pyproject.toml
COPY gateway/ gateway/
COPY mcp_server/ mcp_server/
COPY indexer/ indexer/
COPY embeddings/ embeddings/
COPY prompts/ prompts/
COPY qdrant_manager/ qdrant_manager/
COPY searxng/ searxng/

COPY uv.lock uv.lock

RUN uv sync --frozen --no-dev || uv sync --no-dev

EXPOSE 8000 8001

CMD ["sh", "-c", "exec sleep infinity"]

# CLAUDE.md - Le Petit Prince RAG Pipeline

> RAG (Retrieval-Augmented Generation) pipeline specialized in "Le Petit Prince" by Antoine de Saint-Exupéry. Python-based system with SOLID architecture, communicating with llama.cpp server for embeddings, reranking, and generation.

---

## Table of Contents

1. [Architecture](#1-architecture)
2. [Configuration](#2-configuration)
3. [Core Components](#3-core-components)
4. [API Reference](#4-api-reference)
5. [RAG Pipeline](#5-rag-pipeline)
6. [Frontend](#6-frontend)
7. [Deployment](#7-deployment)
8. [Error Handling](#8-error-handling)
9. [Testing](#9-testing)
10. [Development Guidelines](#10-development-guidelines)

---

## 1. Architecture

### 1.1 Project Structure

```
petit-prince/
├── .venv/
├── frontend/
│   ├── config/
│   │   └── nginx.conf
│   ├── index.html
│   ├── app.js
│   └── README.md
├── src/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application entry point
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py             # Pydantic settings (ENV > .env > .yml)
│   │   └── logging.py              # Logging configuration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py               # Main router
│   │   └── routes/
│   │       ├── init.py             # POST /api/init
│   │       └── chat.py             # POST /api/v1/chat/completions
│   ├── core/
│   │   ├── __init__.py
│   │   ├── interfaces/             # Abstract base classes (SOLID - D)
│   │   │   ├── embedder.py         # IEmbedder protocol
│   │   │   ├── vectorstore.py      # IVectorStore protocol
│   │   │   ├── reranker.py         # IReranker protocol
│   │   │   ├── generator.py        # IGenerator protocol
│   │   │   └── chunker.py          # IChunker protocol
│   │   └── exceptions.py           # Custom exceptions hierarchy
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── service.py              # IngestionService
│   │   ├── reader.py               # TextReader
│   │   ├── chunker.py              # SentenceChunker (ML-based)
│   │   └── paragraph_builder.py    # ParagraphBuilder
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── service.py              # GenerationService
│   │   ├── prompt_builder.py       # PromptBuilder
│   │   └── response_handler.py     # ResponseHandler
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── llama_client.py         # LlamaClient
│   │   └── qdrant_client.py        # QdrantRepository
│   └── utils/
│       ├── __init__.py
│       └── batch.py                # Batch processing utilities
├── scripts/
│   ├── run_api.sh
│   ├── run_start.sh
│   └── run_tests.sh
├── tests/
│   ├── fixtures/
│   ├── integration/
│   ├── unit/
│   ├── conftest.py
│   ├── pytest.ini
│   ├── requirements.txt            # Python dependencies for tests
│   └── README.md
├── va/
│   ├── data/
│   │   └── LePetitPrince.txt                    # Le Petit Prince source text
│   └── gguf_models/
├── compose.yml
├── config.yml                      # Default configuration
├── Dockerfile
├── .env                            # Environment overrides (gitignored)
├── Makefile
├── pyproject.toml
├── QUICKSTART.md
├── README.md
├── requirements.txt                # Python dependencies
└── TESTING.md
```

### 1.2 SOLID Principles

| Principle                     | Application                                                   |
| ----------------------------- | ------------------------------------------------------------- |
| **S** - Single Responsibility | Each class has one job (Reader reads, Chunker chunks)         |
| **O** - Open/Closed           | New chunking strategies via new IChunker implementations      |
| **L** - Liskov Substitution   | All implementations fully substitute their interfaces         |
| **I** - Interface Segregation | Small, focused interfaces (IEmbedder, IReranker, IGenerator)  |
| **D** - Dependency Inversion  | Services depend on abstractions, not concrete implementations |

---

## 2. Configuration

### 2.1 Priority Chain

```
ENV VARIABLES > .env file > config.yml
```

### 2.2 Configuration Schema

```yaml
# config.yml
server:
  host: "0.0.0.0"
  port: 8000

llama:
  embedding_url: "http://llama-embed:8080"
  embedding_model: "Qwen-Embedding"
  rerank_url: "http://llama-rerank:8081"
  reranker_model: "Qwen-Reranker"
  generation_url: "http://llama-gen:8082"
  generation_model: "DeepSeek-R1"
  timeout: 120

qdrant:
  host: "localhost"
  port: 6333
  collection_name: "petit_prince"
  on_disk_payload: true
  distance: "Cosine"

ingestion:
  source_file: "var/data/book.txt"
  sentences_per_paragraph: 10

retrieval:
  top_k: 20 # Initial vector search results
  top_x: 5 # Results after reranking
  relevance_threshold: 0.7

logging:
  level: "INFO"
  format: "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
```

### 2.3 Validation Models

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings

class LlamaConfig(BaseModel):
    base_url: HttpUrl
    embedding_model: str = Field(min_length=1)
    embedding_dim: int = Field(gt=0, le=8192)
    reranker_model: str = Field(min_length=1)
    generation_model: str = Field(min_length=1)
    batch_size: int = Field(gt=0, le=512)
    timeout: int = Field(gt=0, le=600)

class QdrantConfig(BaseModel):
    host: str = Field(min_length=1)
    port: int = Field(gt=0, lt=65536)
    collection_name: str = Field(min_length=1, pattern=r"^[a-z_][a-z0-9_]*$")
    on_disk_payload: bool
    distance: Literal["Cosine", "Euclid", "Dot"]

class RetrievalConfig(BaseModel):
    top_k: int = Field(gt=0, le=1000)
    top_x: int = Field(gt=0, le=100)
    relevance_threshold: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_top_x_less_than_top_k(self) -> "RetrievalConfig":
        if self.top_x > self.top_k:
            raise ValueError(f"top_x ({self.top_x}) must be <= top_k ({self.top_k})")
        return self

class IngestionConfig(BaseModel):
    source_file: Path
    sentences_per_paragraph: int = Field(gt=0, le=100)

    @field_validator("source_file")
    @classmethod
    def validate_file_exists(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"Source file does not exist: {v}")
        return v
```

### 2.4 Startup Validation

```python
def validate_config_at_startup(config: Settings) -> None:
    """Validate all config values and external dependencies."""
    errors = []

    # File existence
    if not config.ingestion.source_file.exists():
        errors.append(f"Source file not found: {config.ingestion.source_file}")

    # Service connectivity (optional)
    try:
        httpx.get(f"{config.llama.base_url}/health", timeout=5)
    except httpx.RequestError as e:
        errors.append(f"Cannot reach llama.cpp at {config.llama.base_url}: {e}")

    # Logical consistency
    if config.retrieval.top_x > config.retrieval.top_k:
        errors.append("top_x cannot exceed top_k")

    if errors:
        raise ConfigurationError(
            f"Configuration validation failed with {len(errors)} error(s)",
            context={"errors": errors}
        )
```

### 2.5 Environment Variables

```bash
LLAMA_BASE_URL=http://gpu-server:8080
LLAMA_EMBEDDING_DIM=768
QDRANT_HOST=qdrant-server
RETRIEVAL_TOP_K=30
LOGGING_LEVEL=DEBUG
```

### 2.6 Fail Fast

L'objectif est de standardiser le code et d'éliminer les erreurs de type.

**Ordre d'exécution recommandé**

1. Black : Formattage automatique.
2. Ruff : Linting rapide (imports, variables inutilisées, style) + corrections automatiques (--fix).
3. Mypy : Vérification stricte du typage

---

## 3. Core Components

### 3.1 Ingestion Pipeline

#### Sentence Chunking (ML-based)

```python
# Recommended: pysbd (rule-based + ML) for French text
# Filter patterns for noise
NOISE_PATTERNS = [
    r"^Chapitre\s+[IVXLCDM]+\.?$",  # Chapter headers
    r"^\d+\.?$",                      # Paragraph numbers
    r"^[IVXLCDM]+\.?$",              # Roman numerals
    r"\[Illustration.*?\]$",         # Image metadata
]

def is_noise(sentence: str) -> bool:
    """Detect structural noise in sentence."""
    sentence = sentence.strip()
    if not sentence:
        return True
    for pattern in NOISE_PATTERNS:
        if re.match(pattern, sentence, re.IGNORECASE):
            return True
    return False
```

#### Paragraph Builder

Groups 10 consecutive sentences to capture context. Single sentences like "Of course." have no semantic meaning for vector search.

```python
# Algorithm: Group 10 consecutive sentences
# Overlap: Optional (e.g., 2 sentences)
# Metadata: Each chunk keeps page/chapter index if available
```

### 3.2 Embedding with llama.cpp

```python
# POST /v1/embeddings - Document embedding
{
    "model": "Qwen",
    "input": ["sentence1", "sentence2", ...],
    "encoding_format": "float"
}

# Query embedding with instruction prefix
{
    "model": "Qwen",
    "input": "Instruct: Given a query, retrieve relevant passages\nQuery: {user_query}",
    "encoding_format": "float"
}
```

### 3.3 Reranking with llama.cpp

```python
# POST /v1/rerank
{
    "model": "ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF:Q8_0",
    "query": "user question",
    "documents": ["doc1", "doc2", ...],
    "top_n": 5
}
```

### 3.4 Qdrant Vector Store

```python
client.create_collection(
    collection_name="petit_prince",
    vectors_config=VectorParams(
        size=1024,
        distance=Distance.COSINE,
        on_disk=True
    ),
    on_disk_payload=True
)
```

---

## 4. API Reference

### 4.1 Endpoints

| Method | Path                       | Description                           |
| ------ | -------------------------- | ------------------------------------- |
| POST   | `/api/init`                | Destroy collection, re-index book.txt |
| POST   | `/api/v1/chat/completions` | OpenAI-compatible chat                |
| GET    | `/health`                  | Service health check                  |
| GET    | `/metrics`                 | Prometheus-style metrics (optional)   |

### 4.2 Chat Request Format

```json
{
  "model": "petit-prince-rag",
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "Qui est le renard?" }
  ],
  "stream": false
}
```

### 4.3 Blocking Response

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "petit-prince-rag",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "..." },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 1847,
    "completion_tokens": 234,
    "total_tokens": 2081
  }
}
```

### 4.4 Streaming Response (SSE)

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"petit-prince-rag","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"petit-prince-rag","choices":[{"index":0,"delta":{"content":"Le"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"petit-prince-rag","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":1847,"completion_tokens":234,"total_tokens":2081}}

data: [DONE]
```

**Note**: `usage` appears only in the final chunk (where `finish_reason` is set).

### 4.5 Extended Metrics

Request with header `X-Include-Metrics: true`:

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "choices": [...],
  "usage": {
    "prompt_tokens": 1847,
    "completion_tokens": 234,
    "total_tokens": 2081
  },
  "x_metrics": {
    "timings": {
      "embedding_ms": 45,
      "search_ms": 12,
      "rerank_ms": 89,
      "generation_ms": 2340,
      "total_ms": 2502
    },
    "retrieval": {
      "documents_retrieved": 20,
      "documents_after_rerank": 5,
      "relevance_scores": [0.92, 0.87, 0.76, 0.71, 0.68],
      "documents_above_threshold": 3,
      "threshold_used": 0.7
    }
  }
}
```

### 4.6 Token Counting

```python
class TokenCounter:
    async def count(self, text: str) -> int:
        """Count tokens using llama.cpp /tokenize endpoint."""
        response = await self.client.post(
            f"{self.base_url}/tokenize",
            json={"content": text}
        )
        return len(response.json()["tokens"])

    async def count_messages(self, messages: list[dict]) -> int:
        """Count tokens for chat messages including special tokens."""
        total = 0
        for msg in messages:
            total += await self.count(msg["content"])
            total += 4  # Role tokens + separators
        total += 2  # BOS/EOS tokens
        return total
```

---

## 5. RAG Pipeline

### 5.1 Pipeline Flow

```
Query → Embed → Search (top_k) → Rerank (top_x) → Build Prompt → Generate
```

### 5.2 Prompt Building Strategy

**All top_x documents from reranker are ALWAYS included in context**, regardless of score. The system prompt instructs the LLM how to interpret them.

#### System Prompt Variants

**Scenario 1: All documents highly relevant** (all scores ≥ threshold)

```
Tu es un expert littéraire spécialisé dans "Le Petit Prince" d'Antoine de Saint-Exupéry.

RÔLE ET IDENTITÉ :
- Tu es un guide bienveillant qui aide à comprendre cette œuvre
- Tu t'exprimes avec clarté, précision et une touche de poésie
- Tu ne prétends jamais être l'auteur ni un personnage du livre

SOURCES À TA DISPOSITION :
Les extraits fournis ci-dessous sont tous hautement pertinents. Tu dois :
- T'appuyer principalement sur ces extraits pour construire ta réponse
- Citer ou paraphraser les passages pertinents
- Rester fidèle au texte original

CONTRAINTES :
- Réponds en français, sauf si l'utilisateur écrit dans une autre langue
- Sois concis mais complet : vise 2-4 paragraphes
- Ne commence jamais par "En tant qu'expert..."
- N'invente jamais de citations qui ne figurent pas dans les extraits
```

**Scenario 2: Partial relevance** (mixed scores)

```
SOURCES À TA DISPOSITION :
Les extraits ont des niveaux de pertinence variables. Chaque extrait est précédé de [PERTINENCE: HAUTE] ou [PERTINENCE: MODÉRÉE].
Tu dois :
- Prioriser les extraits [PERTINENCE: HAUTE]
- Utiliser les extraits [PERTINENCE: MODÉRÉE] comme contexte complémentaire
- Signaler si ta réponse repose sur ta connaissance générale
```

**Scenario 3: No highly relevant documents** (all scores < threshold)

```
SOURCES À TA DISPOSITION :
Les extraits ont une pertinence limitée par rapport à la question posée.
Tu dois :
- Te baser principalement sur ta connaissance générale du Petit Prince
- Mentionner que tu ne disposes pas d'extrait directement pertinent
- Proposer de reformuler la question si elle semble hors sujet
```

### 5.3 Context Injection

Documents are injected into the **last user message**:

```python
def build_user_message_with_context(
    original_query: str,
    documents: list[RankedDocument],
    threshold: float
) -> str:
    context_parts = []
    for i, doc in enumerate(documents, 1):
        tag = "[PERTINENCE: HAUTE]" if doc.score >= threshold else "[PERTINENCE: MODÉRÉE]"
        context_parts.append(f"--- Extrait {i} {tag} ---\n{doc.text}")

    return f"""{original_query}

---
EXTRAITS DU PETIT PRINCE POUR CONTEXTE :

{chr(10).join(context_parts)}
---"""
```

### 5.4 Final Message Assembly

```python
def build_final_messages(
    conversation: list[Message],
    documents: list[RankedDocument],
    threshold: float
) -> list[dict]:
    # 1. Select system prompt variant
    scores = [doc.score for doc in documents]
    if all(s >= threshold for s in scores):
        system_prompt = SYSTEM_PROMPT_ALL_RELEVANT
    elif any(s >= threshold for s in scores):
        system_prompt = SYSTEM_PROMPT_PARTIAL
    else:
        system_prompt = SYSTEM_PROMPT_LOW_RELEVANCE

    # 2. Build messages array
    messages = [{"role": "system", "content": system_prompt}]

    # 3. Add conversation history (all but last)
    for msg in conversation[:-1]:
        messages.append({"role": msg.role, "content": msg.content})

    # 4. Add augmented last user message
    augmented = build_user_message_with_context(
        conversation[-1].content, documents, threshold
    )
    messages.append({"role": "user", "content": augmented})

    return messages
```

### 5.5 Implementation Pattern

```python
async def chat_completion(request: ChatRequest) -> Response:
    # 1. Embed query (blocking - fast)
    query_vector = await embedder.embed_query(request.messages[-1].content)

    # 2. Retrieve & rerank (blocking - fast)
    documents = await retriever.search_and_rerank(query_vector)

    # 3. Build prompt
    prompt = prompt_builder.build(request.messages, documents)

    # 4. Generate
    if request.stream:
        return StreamingResponse(
            generate_stream(prompt),
            media_type="text/event-stream"
        )
    else:
        response = await generator.generate(prompt)
        return JSONResponse(format_completion(response))
```

---

## 6. Frontend

### 6.1 Design Philosophy

- **Minimalist**: Single HTML file with inline CSS, single JS file
- **Zero dependencies**: No frameworks, no build step, no npm
- **Accessible**: Semantic HTML, keyboard navigation, screen reader friendly
- **Responsive**: Works on mobile, tablet, desktop
- **Progressive**: Works without JavaScript (displays message to enable it)

### 6.2 Architecture

```
frontend/
├── index.html    # UI structure with inline CSS
├── app.js        # API communication + DOM manipulation
└── assets/
    └── favicon.svg
```

### 6.3 Layout Structure

```
┌─────────────────────────────────────────┐
│  Le Petit Prince - Assistant Littéraire │  ← Header
├─────────────────────────────────────────┤
│  ┌─────────────────────────────────┐   │
│  │ 👤 User: Qui est le renard?    │   │  ← User message
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │ 📖 Assistant: Le renard est... │   │  ← Assistant message
│  │ [SOURCES] [METRICS] (debug)     │   │
│  └─────────────────────────────────┘   │
├─────────────────────────────────────────┤
│ [ Votre question ici... ]  [Envoyer]    │  ← Input
│ ☐ Mode Debug    🗑️ Effacer             │  ← Controls
└─────────────────────────────────────────┘
```

### 6.4 Features

#### Debug Mode Toggle

When enabled, each assistant message shows collapsible sections:

```
📖 Le renard est un personnage qui enseigne au Petit Prince...

┌─ 📚 SOURCES (5 extraits) ─────────────┐
│ Extrait 1 [PERTINENCE: HAUTE - 0.92]  │
│ "On ne connaît que les choses..."     │
└───────────────────────────────────────┘

┌─ 📊 MÉTRIQUES ─────────────────────────┐
│ Temps total: 2.50s                     │
│   - Embedding: 45ms                    │
│   - Recherche: 12ms                    │
│   - Reranking: 89ms                    │
│   - Génération: 2340ms                 │
│ Tokens: 1847 + 234 = 2081              │
└───────────────────────────────────────┘
```

#### Visual States

1. **Idle**: Input enabled, send button active
2. **Sending**: Input disabled, button shows spinner
3. **Streaming**: Tokens append real-time, typing cursor `▊`
4. **Complete**: Remove cursor, enable input

#### Error Handling

| Error Code | Display                | Action                  |
| ---------- | ---------------------- | ----------------------- |
| 400        | "Question invalide"    | Clear input, focus      |
| 422        | "Format incorrect"     | Show validation hint    |
| 429        | "Trop de requêtes"     | Disable for Retry-After |
| 500        | "Erreur serveur"       | Enable retry button     |
| 503        | "Service indisponible" | Show retry countdown    |
| Network    | "Connexion perdue"     | Auto-retry 3x           |

### 6.5 Complete HTML Implementation

```html
<!DOCTYPE html>
<html lang="fr">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Le Petit Prince - Assistant Littéraire</title>
    <style>
      /* CSS Reset & Base */
      *,
      *::before,
      *::after {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
      }

      :root {
        --primary: #4a90e2;
        --primary-dark: #2e5c8a;
        --secondary: #f5a623;
        --bg-light: #f8f9fa;
        --bg-white: #ffffff;
        --text-dark: #2c3e50;
        --text-muted: #6c757d;
        --border: #dee2e6;
        --error: #e74c3c;
        --success: #27ae60;
        --warning: #f39c12;
        --shadow: rgba(0, 0, 0, 0.1);
        --font-main: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
          Arial, sans-serif;
        --font-mono: "SF Mono", Monaco, "Cascadia Code", monospace;
      }

      body {
        font-family: var(--font-main);
        font-size: 16px;
        line-height: 1.6;
        color: var(--text-dark);
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1rem;
      }

      .container {
        width: 100%;
        max-width: 900px;
        height: 90vh;
        max-height: 800px;
        background: var(--bg-white);
        border-radius: 16px;
        box-shadow: 0 20px 60px var(--shadow);
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }

      .header {
        background: linear-gradient(
          135deg,
          var(--primary) 0%,
          var(--primary-dark) 100%
        );
        color: white;
        padding: 1.5rem;
        text-align: center;
        border-bottom: 3px solid var(--secondary);
      }

      .chat-container {
        flex: 1;
        overflow-y: auto;
        padding: 1.5rem;
        background: var(--bg-light);
        scroll-behavior: smooth;
      }

      .message {
        display: flex;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
        animation: fadeIn 0.3s ease-in;
      }

      @keyframes fadeIn {
        from {
          opacity: 0;
          transform: translateY(10px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }

      .message.user {
        flex-direction: row-reverse;
      }

      .message-avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: var(--primary);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        flex-shrink: 0;
      }

      .message.user .message-avatar {
        background: var(--secondary);
      }

      .message-content {
        max-width: 70%;
        background: white;
        padding: 1rem 1.25rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      }

      .message.user .message-content {
        background: var(--primary);
        color: white;
      }

      .typing-cursor {
        display: inline-block;
        width: 2px;
        height: 1em;
        background: var(--text-dark);
        margin-left: 2px;
        animation: blink 1s infinite;
      }

      @keyframes blink {
        0%,
        49% {
          opacity: 1;
        }
        50%,
        100% {
          opacity: 0;
        }
      }

      .debug-section {
        margin-top: 1rem;
        border-top: 1px solid var(--border);
        padding-top: 1rem;
      }

      .debug-section summary {
        cursor: pointer;
        font-weight: 600;
        color: var(--primary);
      }

      .input-area {
        padding: 1rem 1.5rem;
        background: white;
        border-top: 1px solid var(--border);
      }

      .input-wrapper {
        display: flex;
        gap: 0.75rem;
        margin-bottom: 0.75rem;
      }

      .input-field {
        flex: 1;
        padding: 0.75rem 1rem;
        border: 2px solid var(--border);
        border-radius: 8px;
        font-size: 1rem;
      }

      .input-field:focus {
        outline: none;
        border-color: var(--primary);
      }

      .send-button {
        padding: 0.75rem 1.5rem;
        background: var(--primary);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
      }

      .send-button:hover:not(:disabled) {
        background: var(--primary-dark);
      }
      .send-button:disabled {
        background: var(--text-muted);
        cursor: not-allowed;
      }

      .toast-container {
        position: fixed;
        top: 2rem;
        right: 2rem;
        z-index: 1000;
      }

      .toast {
        min-width: 300px;
        padding: 1rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px var(--shadow);
        animation: slideIn 0.3s ease-out;
      }

      @keyframes slideIn {
        from {
          transform: translateX(100%);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }

      .toast.error {
        border-left: 4px solid var(--error);
      }
      .toast.success {
        border-left: 4px solid var(--success);
      }
      .toast.warning {
        border-left: 4px solid var(--warning);
      }

      @media (max-width: 768px) {
        .container {
          max-height: 100vh;
          height: 100vh;
          border-radius: 0;
        }
        .message-content {
          max-width: 85%;
        }
      }
    </style>
  </head>
  <body>
    <div class="container">
      <header class="header">
        <h1>Le Petit Prince - Assistant Littéraire</h1>
        <p>Explorez l'œuvre d'Antoine de Saint-Exupéry avec l'aide de l'IA</p>
      </header>

      <div id="initBanner" class="init-banner">
        <p>⚠️ L'index n'est pas encore initialisé</p>
        <button id="initButton" class="init-button">
          📥 Initialiser l'index
        </button>
      </div>

      <main
        id="chatContainer"
        class="chat-container"
        role="log"
        aria-live="polite"
      ></main>

      <div class="input-area">
        <div class="input-wrapper">
          <input
            type="text"
            id="messageInput"
            class="input-field"
            placeholder="Posez votre question sur Le Petit Prince..."
            aria-label="Champ de question"
            autocomplete="off"
          />
          <button id="sendButton" class="send-button">Envoyer</button>
        </div>
        <div class="controls">
          <label class="checkbox-wrapper">
            <input type="checkbox" id="debugToggle" />
            <span>Mode Debug</span>
          </label>
          <button id="clearButton" class="clear-button">🗑️ Effacer</button>
        </div>
      </div>
    </div>

    <div
      id="toastContainer"
      class="toast-container"
      role="status"
      aria-live="polite"
    ></div>
    <script src="app.js"></script>
  </body>
</html>
```

### 6.6 Complete JavaScript Implementation

```javascript
/**
 * Le Petit Prince RAG Frontend - Pure vanilla JavaScript
 */

const CONFIG = {
  API_BASE_URL: window.location.origin,
  ENDPOINTS: {
    CHAT: "/api/v1/chat/completions",
    INIT: "/api/init",
    HEALTH: "/health",
  },
  STORAGE_KEYS: {
    CONVERSATION: "lpp_conversation",
    DEBUG_MODE: "lpp_debug_mode",
  },
  TOAST_DURATION: 5000,
};

const state = {
  conversation: [],
  debugMode: false,
  isStreaming: false,
};

const elements = {
  chatContainer: document.getElementById("chatContainer"),
  messageInput: document.getElementById("messageInput"),
  sendButton: document.getElementById("sendButton"),
  debugToggle: document.getElementById("debugToggle"),
  clearButton: document.getElementById("clearButton"),
  initBanner: document.getElementById("initBanner"),
  initButton: document.getElementById("initButton"),
  toastContainer: document.getElementById("toastContainer"),
};

function init() {
  loadDebugMode();
  loadConversation();
  checkAPIHealth();
  attachEventListeners();
  elements.messageInput.focus();
}

function attachEventListeners() {
  elements.sendButton.addEventListener("click", handleSendMessage);
  elements.messageInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });
  elements.debugToggle.addEventListener("change", handleDebugToggle);
  elements.clearButton.addEventListener("click", handleClearConversation);
  elements.initButton.addEventListener("click", handleInitIndex);
}

async function checkAPIHealth() {
  try {
    const response = await fetch(
      `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.HEALTH}`
    );
    if (!response.ok) showToast("Service indisponible", "error");
  } catch (error) {
    showToast("Impossible de contacter le serveur", "error");
  }
}

async function handleSendMessage() {
  const text = elements.messageInput.value.trim();
  if (!text || state.isStreaming) return;

  const userMessage = { role: "user", content: text, timestamp: Date.now() };
  addMessageToConversation(userMessage);
  renderMessage(userMessage);

  elements.messageInput.value = "";
  setInputState(false);
  await sendMessageToAPI();
}

async function sendMessageToAPI() {
  state.isStreaming = true;
  const messages = state.conversation.map((m) => ({
    role: m.role,
    content: m.content,
  }));
  const headers = { "Content-Type": "application/json" };
  if (state.debugMode) headers["X-Include-Metrics"] = "true";

  try {
    const response = await fetch(
      `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.CHAT}`,
      {
        method: "POST",
        headers,
        body: JSON.stringify({
          model: "petit-prince-rag",
          messages,
          stream: true,
        }),
      }
    );

    if (!response.ok) {
      await handleAPIError(response);
      return;
    }
    await handleStreamingResponse(response);
  } catch (error) {
    showToast("Connexion perdue", "error");
  } finally {
    state.isStreaming = false;
    setInputState(true);
    elements.messageInput.focus();
  }
}

async function handleStreamingResponse(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  const assistantMessage = {
    role: "assistant",
    content: "",
    timestamp: Date.now(),
  };
  addMessageToConversation(assistantMessage);
  const messageElement = renderMessage(assistantMessage, true);
  const contentElement = messageElement.querySelector(".message-text");

  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.trim() || !line.startsWith("data: ")) continue;
      const data = line.slice(6);

      if (data === "[DONE]") {
        removeTypingCursor(contentElement);
        saveConversation();
        continue;
      }

      try {
        const chunk = JSON.parse(data);
        if (chunk.choices?.[0]?.delta?.content) {
          assistantMessage.content += chunk.choices[0].delta.content;
          updateMessageContent(contentElement, assistantMessage.content, true);
          scrollToBottom();
        }
        if (chunk.usage && state.debugMode) {
          assistantMessage.metrics = {
            usage: chunk.usage,
            ...(chunk.x_metrics || {}),
          };
          renderDebugInfo(messageElement, assistantMessage.metrics);
        }
      } catch (e) {
        console.error("Parse error:", e);
      }
    }
  }
}

function renderMessage(message, isStreaming = false) {
  const div = document.createElement("div");
  div.className = `message ${message.role}`;

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = message.role === "user" ? "👤" : "📖";

  const content = document.createElement("div");
  content.className = "message-content";

  const text = document.createElement("p");
  text.className = "message-text";
  updateMessageContent(text, message.content, isStreaming);

  const timestamp = document.createElement("small");
  timestamp.className = "message-timestamp";
  timestamp.textContent = new Date(message.timestamp).toLocaleTimeString(
    "fr-FR",
    {
      hour: "2-digit",
      minute: "2-digit",
    }
  );

  content.appendChild(text);
  content.appendChild(timestamp);
  div.appendChild(avatar);
  div.appendChild(content);
  elements.chatContainer.appendChild(div);
  scrollToBottom();

  return div;
}

function updateMessageContent(element, content, showCursor) {
  element.textContent = content;
  if (showCursor) {
    const cursor = document.createElement("span");
    cursor.className = "typing-cursor";
    element.appendChild(cursor);
  }
}

function removeTypingCursor(element) {
  const cursor = element.querySelector(".typing-cursor");
  if (cursor) cursor.remove();
}

function showToast(message, type = "error") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  const icons = { error: "❌", success: "✅", warning: "⚠️" };
  toast.innerHTML = `<span>${icons[type]}</span> <span>${message}</span>`;
  elements.toastContainer.appendChild(toast);
  setTimeout(() => toast.remove(), CONFIG.TOAST_DURATION);
}

function addMessageToConversation(message) {
  state.conversation.push(message);
  saveConversation();
}

function loadConversation() {
  const stored = localStorage.getItem(CONFIG.STORAGE_KEYS.CONVERSATION);
  if (stored) {
    state.conversation = JSON.parse(stored);
    state.conversation.forEach((msg) => renderMessage(msg));
  }
}

function saveConversation() {
  localStorage.setItem(
    CONFIG.STORAGE_KEYS.CONVERSATION,
    JSON.stringify(state.conversation)
  );
}

function handleClearConversation() {
  if (!confirm("Effacer toute la conversation ?")) return;
  state.conversation = [];
  elements.chatContainer.innerHTML = "";
  saveConversation();
  showToast("Conversation effacée", "success");
}

function loadDebugMode() {
  state.debugMode =
    localStorage.getItem(CONFIG.STORAGE_KEYS.DEBUG_MODE) === "true";
  elements.debugToggle.checked = state.debugMode;
}

function handleDebugToggle(event) {
  state.debugMode = event.target.checked;
  localStorage.setItem(CONFIG.STORAGE_KEYS.DEBUG_MODE, state.debugMode);
}

function setInputState(enabled) {
  elements.messageInput.disabled = !enabled;
  elements.sendButton.disabled = !enabled;
  elements.sendButton.textContent = enabled ? "Envoyer" : "⏳";
}

function scrollToBottom() {
  elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

async function handleAPIError(response) {
  const data = await response.json().catch(() => ({}));
  const msg = data.error?.message || "Erreur inconnue";

  switch (response.status) {
    case 400:
      if (msg.includes("init")) elements.initBanner.classList.add("show");
      showToast(msg, "error");
      break;
    case 422:
      showToast("Format incorrect", "error");
      break;
    case 429:
      showToast("Trop de requêtes", "warning");
      break;
    case 503:
      showToast("Service indisponible", "error");
      break;
    default:
      showToast("Erreur serveur", "error");
  }
}

async function handleInitIndex() {
  elements.initButton.disabled = true;
  elements.initButton.textContent = "⏳ Initialisation...";

  try {
    const response = await fetch(
      `${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.INIT}`,
      {
        method: "POST",
      }
    );
    if (response.ok) {
      showToast("Index initialisé", "success");
      elements.initBanner.classList.remove("show");
    } else {
      showToast("Échec de l'initialisation", "error");
    }
  } catch (e) {
    showToast("Erreur réseau", "error");
  } finally {
    elements.initButton.disabled = false;
    elements.initButton.textContent = "📥 Initialiser l'index";
  }
}

document.addEventListener("DOMContentLoaded", init);
```

### 6.7 Conversation Persistence

```javascript
// Store in localStorage
{
  role: "user" | "assistant",
  content: string,
  timestamp: number,
  metrics?: object
}
```

### 6.8 Initialization Flow

1. Check API health: `GET /health`
2. Check if index exists (detect via first API call)
3. If uninitialized: Show "📥 Initialiser l'index" button
4. Restore conversation from localStorage
5. Focus on input field

---

## 7. Deployment

### 7.1 Docker Compose Services

| Service      | Description        | Port |
| ------------ | ------------------ | ---- |
| qdrant       | Vector database    | 6333 |
| llama-embed  | Embedding server   | 8080 |
| llama-rerank | Reranking server   | 8081 |
| llama-gen    | Generation server  | 8082 |
| api          | FastAPI backend    | 8000 |
| frontend     | Nginx static files | 80   |

### 7.2 compose.yml

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: petit-prince-qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 10s
      retries: 5

  llama-embed:
    image: ghcr.io/ggerganov/llama.cpp:server
    profiles: ["cpu", "gpu", "mps"]
    command: -m /models/embed.gguf --embedding --port 8080 --host 0.0.0.0 -cb
    volumes:
      - ./var/models:/models
    deploy: &gpu_config
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  llama-rerank:
    image: ghcr.io/ggerganov/llama.cpp:server
    profiles: ["cpu", "gpu", "mps"]
    command: -m /models/rerank.gguf --reranking --port 8081 --host 0.0.0.0 -cb
    volumes:
      - ./var/models:/models
    deploy: *gpu_config

  llama-gen:
    image: ghcr.io/ggerganov/llama.cpp:server
    profiles: ["cpu", "gpu", "mps"]
    command: -m /models/gen.gguf -c 4096 -ngl 99 --port 8082 --host 0.0.0.0
    volumes:
      - ./var/models:/models
    deploy: *gpu_config

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: petit-prince-api
    environment:
      - QDRANT_HOST=qdrant
      - LLAMA_EMBEDDING_URL=http://llama-embed:8080
      - LLAMA_RERANK_URL=http://llama-rerank:8081
      - LLAMA_GENERATION_URL=http://llama-gen:8082
    depends_on:
      qdrant:
        condition: service_healthy
    ports:
      - "8000:8000"

  frontend:
    image: nginx:alpine
    container_name: petit-prince-front
    volumes:
      - ./src/frontend:/usr/share/nginx/html:ro
      - ./config/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "80:80"
    depends_on:
      api:
        condition: service_healthy

volumes:
  qdrant_data:
```

### 7.3 Launch Commands

```bash
# CPU profile (Mac Intel / Linux without GPU)
docker compose --profile cpu up -d

# GPU profile (Linux + Nvidia)
docker compose --profile gpu up -d

# MPS profile (Apple Silicon - often mapped to CPU in Docker)
docker compose --profile mps up -d
```

### 7.4 Nginx Configuration

```nginx
server {
    listen 80;
    server_name localhost;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
    }

    location /api/ {
        proxy_pass http://api:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # Streaming support
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;
    }

    location /health {
        proxy_pass http://api:8000/health;
    }

    location ~* \.(css|js|jpg|jpeg|png|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 7.5 Health Checks

At FastAPI lifespan startup, perform blocking checks:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup checks
    await check_qdrant_health()
    await check_llama_health()
    yield
    # Shutdown
    await cleanup()
```

---

## 8. Error Handling

### 8.1 Exception Hierarchy

```python
class PetitPrinceError(Exception):
    """Base exception with context preservation."""
    def __init__(self, message: str, context: dict | None = None):
        self.context = context or {}
        super().__init__(message)

class IngestionError(PetitPrinceError): ...
class EmbeddingError(PetitPrinceError): ...
class RetrievalError(PetitPrinceError): ...
class GenerationError(PetitPrinceError): ...
class ConfigurationError(PetitPrinceError): ...
```

### 8.2 Error Raising Guidelines

```python
# ❌ Bad: vague message
raise EmbeddingError("Embedding failed")

# ✅ Good: precise context with debugging info
raise EmbeddingError(
    f"Embedding batch failed: llama.cpp returned status {response.status_code}",
    context={
        "batch_size": len(texts),
        "model": self.config.embedding_model,
        "endpoint": f"{self.base_url}/v1/embeddings",
        "response_body": response.text[:500],
    }
)
```

### 8.3 Error Propagation

```python
try:
    vectors = await self.embedder.embed_batch(chunks)
except httpx.TimeoutException as e:
    raise EmbeddingError(
        f"Llama.cpp timeout after {self.config.timeout}s",
        context={"chunks_sample": chunks[:2], "timeout": self.config.timeout}
    ) from e  # Preserve original traceback
```

### 8.4 HTTP Error Response Format

```json
{
  "error": {
    "type": "embedding_error",
    "message": "Failed to embed query: connection refused",
    "details": {
      "service": "llama.cpp",
      "endpoint": "/v1/embeddings",
      "suggestion": "Verify llama.cpp server is running"
    }
  }
}
```

### 8.5 Robustness: Edge Cases

#### Ingestion Failures

| Scenario                     | Expected Behavior                                           |
| ---------------------------- | ----------------------------------------------------------- |
| Source file empty            | `IngestionError("Source file is empty: {path}")`, HTTP 422  |
| Source file not UTF-8        | Attempt fallback encodings, or raise with detected encoding |
| Only noise in file           | `IngestionError("No valid sentences extracted")`            |
| Qdrant unreachable           | Retry 3x with exponential backoff                           |
| Embedding batch fails        | Log batch index, retry failed batch 2x                      |
| Embedding dimension mismatch | `EmbeddingError(f"Expected {expected}, got {actual}")`      |

#### Retrieval Failures

| Scenario                  | Expected Behavior                            |
| ------------------------- | -------------------------------------------- |
| Wrong embedding dimension | `EmbeddingError` with expected vs actual     |
| Empty/NaN/Inf vector      | `EmbeddingError("Invalid embedding values")` |
| Qdrant timeout            | Retry 2x with shorter top_k                  |
| Qdrant returns 0 results  | Continue with "no context" prompt variant    |
| Reranker unavailable      | Fallback to vector similarity ranking        |
| Invalid reranker scores   | Validate scores, fallback to vector ranking  |

#### Generation Failures

| Scenario                | Expected Behavior                            |
| ----------------------- | -------------------------------------------- |
| LLM unavailable         | Retry 2x, then HTTP 503                      |
| LLM timeout             | HTTP 504 with partial context                |
| Stream connection drops | Server logs warning with last chunk index    |
| Client disconnects      | Stop generation, log `"client_disconnected"` |
| Empty response          | Retry once with modified prompt              |
| Token limit exceeded    | Truncate context (keep most relevant docs)   |

### 8.6 Retry Configuration

```python
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    retryable_exceptions: tuple = (httpx.TimeoutException, httpx.NetworkError)
    retryable_status_codes: tuple = (429, 500, 502, 503, 504)

async def with_retry(func: Callable, config: RetryConfig, context: str) -> Any:
    """Execute function with retry logic."""
    last_exception = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            return await func()
        except config.retryable_exceptions as e:
            last_exception = e
            delay = min(
                config.base_delay * (config.exponential_base ** (attempt - 1)),
                config.max_delay
            )
            logger.warning(
                "Retry %d/%d for %s: %s. Waiting %.1fs",
                attempt, config.max_attempts, context, str(e), delay
            )
            await asyncio.sleep(delay)

    raise last_exception
```

---

## 9. Testing

### 9.1 Prerequisites

The goal is to standardize the code and eliminate type-related errors **before** the Python interpreter even runs unit tests, by enforcing a _Quality Gate_ following the **Fail Fast** principles defined in [FailTest](#26-fail-fast):

1. **Black**: Automatic code formatting.
2. **Ruff**: Fast linting (imports, unused variables, style) + automatic fixes (`--fix`).
3. **Mypy**: Strict static type checking.
4. **Tests (Pytest)**: Executed only if all previous steps pass.

---

### 9.2 Unit Tests

#### 1. Configuration (`src/config/settings.py`)

**Nominal Cases:**

- `test_load_settings_from_valid_yaml`: Verifies that `config.yml` is correctly loaded.
- `test_env_vars_override_yaml`: Verifies that environment variables (e.g. `LLAMA__BASE_URL`) correctly override YAML values.
- `test_default_values`: Verifies that default values are applied when optional fields are missing.

**Edge / Error Cases:**

- `test_missing_config_file`: Verifies behavior when `config.yml` is missing (load defaults or raise an error depending on the logic).
- `test_invalid_yaml_syntax`: Raises `ConfigurationError` if the YAML is malformed.
- `test_validation_embedding_dim_constraints`: Raises an error if `embedding_dim <= 0` or `> 8192`.
- `test_validation_top_x_greater_than_top_k`: Raises an error if `top_x > top_k` (business logic).
- `test_validation_invalid_url`: Raises an error if `base_url` does not start with `http/https`.
- `test_validation_source_file_not_found`: Raises an error if the specified source file does not exist.

---

#### 2. Utilities (`src/utils/batch.py`)

**Nominal Cases:**

- `test_batched_exact_division`: Split a list of 10 elements into batches of 2 (expect 5 batches).
- `test_batched_with_remainder`: Split a list of 10 elements into batches of 3 (3 batches of 3 + 1 batch of 1).

**Edge / Error Cases:**

- `test_batched_empty_list`: Returns an empty list.
- `test_batched_size_larger_than_list`: Returns a single batch containing the entire list.
- `test_batched_zero_or_negative_size`: Must raise `ValueError`.

---

#### 3. Ingestion Layer

##### A. Reader (`src/ingestion/reader.py`)

**Nominal Cases:**

- `test_read_utf8_file`: Correctly reads a standard UTF-8 text file.

**Edge / Error Cases:**

- `test_read_non_existent_file`: Raises `IngestionError`.
- `test_read_empty_file`: Raises `IngestionError`.
- `test_read_encoding_fallback`: Tests reading a Latin-1 encoded file (fallback).
- `test_read_whitespace_only_file`: Raises `IngestionError` if the file contains only whitespace.

---

##### B. Chunker (`src/ingestion/chunker.py`)

**Nominal Cases:**

- `test_chunk_simple_sentences`: Splits a standard paragraph into sentences.
- `test_chunk_dialogue`: Correctly handles dialogues (quotes, dashes).
- `test_chunk_ellipsis`: Does not split on `"..."` within a sentence.

**Edge / Error Cases:**

- `test_chunk_empty_text`: Returns an empty list.
- `test_chunk_noise_filtering`: Verifies that `"Chapitre I"`, `"IV"`, `"1."` are filtered out (noise regex).
- `test_chunk_very_long_sentence`: Verifies that a sentence longer than 1000 characters is handled (and logged as a warning).
- `test_chunk_no_valid_sentences`: Raises `IngestionError` if the text contains only noise.

---

##### C. ParagraphBuilder (`src/ingestion/paragraph_builder.py`)

**Nominal Cases:**

- `test_build_paragraphs_exact_count`: Groups X sentences into Y complete paragraphs.
- `test_build_paragraphs_with_remainder`: The last paragraph contains the remaining sentences.

**Edge / Error Cases:**

- `test_build_empty_input`: Returns an empty list.
- `test_build_sentences_fewer_than_chunk_size`: Returns a single paragraph.

---

##### D. IngestionService (`src/ingestion/service.py`)

_Requires mocks for Reader, Chunker, Embedder, VectorStore._

**Nominal Cases:**

- `test_ingest_full_pipeline_success`: Verifies the sequential calls: Read → Chunk → Build → Create Collection → Embed Batch → Upsert. Verifies returned statistics.

**Edge / Error Cases:**

- `test_ingest_embedder_failure`: Raises (or propagates) `IngestionError` if embedding fails.
- `test_ingest_vectorstore_failure`: Raises `VectorStoreError` if collection creation or upsert fails.

---

#### 4. Infrastructure Layer (Adapters)

##### A. LlamaClient (`src/infrastructure/llama_client.py`)

_Requires `pytest-httpx` to mock external API calls._

**Nominal Cases:**

- `test_embed_batch_success`: Returns vectors with correct dimensions.
- `test_rerank_success`: Returns sorted documents with scores.
- `test_generate_blocking_success`: Returns generated text.
- `test_generate_streaming_success`: Returns an iterator of chunks.

**Edge / Error Cases:**

- `test_embed_dimension_mismatch`: Raises `EmbeddingError` if returned dimension ≠ configured dimension.
- `test_embed_api_timeout`: Verifies retry logic, then raises an error.
- `test_embed_api_500_error`: Raises `EmbeddingError` after retries.
- `test_embed_nan_values`: Raises an error if the vector contains NaN/Inf values.
- `test_generate_empty_response`: Handles the case where the API returns an empty string.

---

##### B. QdrantRepository (`src/infrastructure/qdrant_client.py`)

_Requires mocks of `AsyncQdrantClient`._

**Nominal Cases:**

- `test_create_collection_idempotency`: Deletes existing collection if needed, then creates a new one.
- `test_upsert_vectors`: Verifies that points are correctly structured (UUID IDs, payload).
- `test_search_vectors`: Verifies mapping from Qdrant response to `SearchResult`.

**Edge / Error Cases:**

- `test_upsert_mismatch_count`: Raises an error if the number of texts ≠ number of vectors.
- `test_search_connection_error`: Raises `VectorStoreError` if Qdrant is unreachable.
- `test_create_collection_failure`: Raises `VectorStoreError` on API failure.

---

#### 5. Generation Layer

##### A. PromptBuilder (`src/generation/prompt_builder.py`)

**Nominal Cases:**

- `test_build_prompt_high_relevance`: Uses `SYSTEM_PROMPT_ALL_RELEVANT` if all scores exceed the threshold.
- `test_build_prompt_mixed_relevance`: Uses `SYSTEM_PROMPT_PARTIAL` if scores are mixed.
- `test_build_prompt_low_relevance`: Uses `SYSTEM_PROMPT_LOW_RELEVANCE` if no score exceeds the threshold.
- `test_context_injection_format`: Verifies that documents are correctly formatted with `[RELEVANCE: ...]` tags.

**Edge / Error Cases:**

- `test_build_prompt_no_documents`: Handles an empty document list (fallback to low relevance).
- `test_build_prompt_history_preservation`: Verifies that conversation history is preserved before the last user message.

---

##### B. ResponseHandler (`src/generation/response_handler.py`)

**Nominal Cases:**

- `test_format_blocking_response`: Verifies compliance with the OpenAI schema (`id`, `object`, `choices`, `usage`).
- `test_format_streaming_chunks`: Verifies SSE format (`data: {...}`).
- `test_extended_metrics_inclusion`: Verifies that `x_metrics` is included when requested.

**Edge / Error Cases:**

- `test_format_usage_calculation`: Verifies that `total_tokens = prompt_tokens + completion_tokens`.

---

##### C. GenerationService (`src/generation/service.py`)

_Requires mocks for Embedder, VectorStore, Reranker, Generator._

**Nominal Cases:**

- `test_process_query_standard_flow`: Embed Query → Search → Rerank → Build Prompt.

**Edge / Error Cases:**

- `test_process_query_no_search_results`: Stops the pipeline after search (no rerank) and returns an empty list.
- `test_process_query_reranker_failure`: Fallback: uses vector search results if the reranker raises `RerankError`.
- `test_token_counting_failure`: Uses estimation if token counting fails.

---

#### 6. API Layer (`src/api/`)

##### A. Init Endpoint (`src/api/routes/init.py`)

**Nominal Cases:**

- `test_api_init_success`: Returns HTTP 200 with stats JSON.

**Error Handling (Edge Cases):**

- `test_api_init_ingestion_error_422`: Simulate an `IngestionError` (e.g. empty source file). Verify HTTP 422 Unprocessable Entity with error details.
- `test_api_init_vectorstore_error_500`: Simulate a `VectorStoreError` (e.g. Qdrant connection failure). Verify HTTP 500 Internal Server Error.
- `test_api_init_unexpected_error_500`: Simulate a generic exception (`RuntimeError`). Verify HTTP 500 without crashing the server.

---

##### B. Chat Endpoint (`src/api/routes/chat.py`)

**Nominal Cases:**

- `test_api_chat_blocking_success`: Returns full JSON response.
- `test_api_chat_streaming_success`: Returns a `StreamingResponse` with correct content-type.
- `test_api_chat_with_metrics_header`: Verifies that `x_metrics` is included if the header is present.

**Edge / Error Cases:**

- `test_api_chat_empty_messages`: Returns HTTP 422.
- `test_api_chat_retrieval_service_unavailable`: Returns HTTP 503 if vector search fails.
- `test_api_chat_generation_service_unavailable`: Returns HTTP 503 if the LLM fails.
- `test_api_chat_token_estimation_fallback`: Verifies that a response is returned even if token counting fails.
- `test_api_chat_validation_error_422`: Send invalid JSON payload (e.g. empty messages list). Verify HTTP 422 Validation Error.
- `test_api_chat_retrieval_error_503`: Mock `GenerationService.process_query` to raise `RetrievalError` (e.g. Qdrant down). Verify HTTP 503 with `retrieval_error` type in JSON.
- `test_api_chat_generation_error_503`: Mock service to raise `GenerationError` (e.g. Llama.cpp timeout). Verify HTTP 503.
- `test_api_chat_internal_error_500`: Simulate an unexpected pipeline crash. Verify HTTP 500 and ensure stack traces are not exposed to the client (security).
- `test_api_chat_streaming_disconnect`: Simulate a client disconnect during streaming (`GeneratorExit`). Verify that resources are cleaned up and the event is logged without critical errors.

---

#### 7. Performance & Metrics (New Section)

These tests validate response time calculations and the efficiency of critical components. They do not replace load testing, but ensure that measurement tools function correctly.

##### A. Metrics (`src/generation/response_handler.py`)

**Nominal Cases:**

- `test_metrics_calculation_accuracy`: Create a `RequestMetrics` object, simulate delays (mocked `time.sleep`), and verify that `total_ms` matches the sum or start/end delta.
- `test_metrics_token_sum`: Verify that `total_tokens` is strictly the sum of `prompt_tokens + completion_tokens`.
- `test_extended_metrics_structure`: Verify that `to_extended_metrics()` generates the JSON structure expected by the frontend (timings, retrieval, etc.).

---

##### B. Unit Benchmarks (with `pytest-benchmark`)

- `test_benchmark_chunker_speed`: Measure chunking time for a 1MB text. Must remain below a defined threshold (e.g. < 50ms).
- `test_benchmark_prompt_builder_overhead`: Measure prompt construction time with maximum context (e.g. 20 documents). Must be negligible (< 1ms).
- `test_benchmark_json_serialization`: Verify that serialization of large response objects (with extended metrics) does not introduce perceptible latency.

---

##### C. Timeout and Latency Handling

- `test_service_timeout_propagation`: Verify that when `LlamaClient` raises a timeout (configured at 120s in `config.yml`), the error propagates to the API as HTTP 503 or 504 Gateway Timeout.

### 9.3 Integration Tests (Full Pipeline)

#### Simulated test

These tests simulate end-to-end operation, ideally with very realistic test containers or mocks.

**test_indexing**

1. Index the document through the pipeline /init
   **test_reindexing:**

1. Index once.
1. Reindex (Check that the collection is indeed deleted/recreated and not duplicated).

**test_generate:**

1. Simulate with mocks a retrieve and rerank with fake documents.
2. Send a Chat request "Who is the fox?".
3. Check that the response contains citations (proof that the context was used).
4. Check the returned metrics.

#### Non-isolated tests

These tests have as a prerequisite to test the connections with the other Llama and Qdrant entities.

\*test_init:\*\*
Completely ingest by the API a short document mastered and finally checks the state of the Qdrant database and what is expected in function of the initial document.

\*test_chat\*\*
Must send a simple API request and retrieve a valid and expected response.

**test_chat_concurrence\***:
This is a test to verify that the API correctly handles concurrent chat requests.

### 9.4 Testing scripts and deployment.

- **test_run_api**: tests the script run_api.sh
- **test_run_start** : tests the script run_start.sh
- **test_run_test**: tests the script run_test.sh
- **test_docker**: tests the containerization in docker of the project
- **test_docker_profile**: tests the docker implementation of the project according to the 3 defined profiles

### 9.5 Tests and deep semantic analysis:

Pylint should be used for deep semantic analysis, duplicate code detection and cyclomatic complexity.

---

# 10. Development Guidelines

## 10.1 Logging

Format: `timestamp | LEVEL | module:function:line | message`

| Level    | Use Case                                        |
| -------- | ----------------------------------------------- |
| DEBUG    | Batch progress, vector dimensions, raw scores   |
| INFO     | Pipeline stages, API calls, indexation progress |
| WARNING  | Low relevance scores, retry attempts, fallbacks |
| ERROR    | API failures, parsing errors, connection issues |
| CRITICAL | Service unavailable, data corruption            |

```python
logger.info("Starting ingestion from %s", config.source_file)
logger.debug("Chunked into %d sentences, %d paragraphs", n_sent, n_para)
logger.warning("Reranker returned no documents above threshold %.2f", threshold)
logger.error("Qdrant connection failed: %s", str(e))
```

### 10.2 Docstrings (Google Style)

```python
def embed_batch(self, texts: list[str]) -> list[list[float]]:
    """Embed multiple texts using llama.cpp server.

    Args:
        texts: List of texts to embed.

    Returns:
        List of embedding vectors.

    Raises:
        EmbeddingError: If llama.cpp server returns an error.
    """
```

### 10.3 Comments Policy

```python
# ✅ Good: Explain WHY
# Filter chapter headers that pysbd incorrectly identifies as sentences
if CHAPTER_PATTERN.match(sentence):
    continue

# ❌ Bad: Restate WHAT
# Loop through sentences
for sentence in sentences:
```

### 10.4 Type Hints

Use modern Python 3.11+ syntax:

```python
# ✅ Good
def process(items: list[str]) -> dict[str, int]: ...

# ❌ Bad
def process(items: List[str]) -> Dict[str, int]: ...
```

### 10.5 Implementation Priority

1. **Start with interfaces** in `core/interfaces/` before implementations
2. **Config first**: Implement settings.py with full priority chain
3. **Test chunking** on actual book.txt - French text has specific patterns
4. **Batch wisely**: llama.cpp has context limits
5. **Log generously at DEBUG level** - RAG debugging requires visibility

### 10.6 Test Writing Guidelines

1. **Priority**: Infrastructure → Integration → Edge Cases → Performance
2. **Always mock external services** in unit tests
3. **Use parametrize** for multiple scenarios:

```python
@pytest.mark.parametrize("dim,expected_error", [
    (0, "must be greater than 0"),
    (-1, "must be greater than 0"),
    (10000, "must be less than 8192"),
])
def test_invalid_embedding_dim(dim, expected_error):
    ...
```

4. **Markers are mandatory**: `@pytest.mark.edge_case`, `@pytest.mark.integration`
5. **Specific assertions**:

```python
# ❌ Bad
assert "error" in str(exc)

# ✅ Good
assert "Embedding dimension mismatch: expected 1024, got 768" in str(exc.value)
```

6. **Docstrings are mandatory** - they serve as living documentation

---

## Quick Reference

### Commands

```bash
# Run server
uvicorn src.main:app --host 0.0.0.0 --port 8000

# Initialize index
curl -X POST http://localhost:8000/api/init

# Chat (blocking)
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Qui est le petit prince?"}]}'

# Chat (streaming)
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" -N \
  -d '{"messages": [{"role": "user", "content": "Qui est le petit prince?"}], "stream": true}'

# Chat with metrics
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Include-Metrics: true" \
  -d '{"messages": [{"role": "user", "content": "Qui est le petit prince?"}]}'
```

### Dependencies

```
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
httpx>=0.26.0
qdrant-client>=1.7.0
pysbd>=0.3.4
python-dotenv>=1.0.0
pyyaml>=6.0.1
```

### Test Dependencies

```
pytest
pytest-asyncio
pytest-httpx
pytest-mock
pytest-cov
```

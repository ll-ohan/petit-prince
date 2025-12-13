# CLAUDE.md - Le Petit Prince RAG Pipeline

## Project Overview

RAG (Retrieval-Augmented Generation) pipeline specialized in "Le Petit Prince" by Antoine de Saint-Exupéry. Python-based system with SOLID architecture, communicating with llama.cpp server (swap-enabled) for embeddings, reranking, and generation.

## Architecture

```
src/
├── __init__.py
├── main.py                     # FastAPI application entry point
├── config/
│   ├── __init__.py
│   ├── settings.py             # Pydantic settings with ENV > .env > .yml priority
│   └── logging.py              # Logging configuration with function/line display
├── api/
│   ├── __init__.py
│   ├── router.py               # Main router aggregating all routes
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── init.py             # POST /api/init - Indexation trigger
│   │   └── chat.py             # POST /api/v1/chat - OpenAI-compatible endpoint
│   └── schemas/
│       ├── __init__.py
│       ├── chat.py             # OpenAI chat request/response schemas
│       └── init.py             # Init endpoint schemas
├── core/
│   ├── __init__.py
│   ├── interfaces/             # Abstract base classes (SOLID - D)
│   │   ├── __init__.py
│   │   ├── embedder.py         # IEmbedder protocol
│   │   ├── vectorstore.py      # IVectorStore protocol
│   │   ├── reranker.py         # IReranker protocol
│   │   ├── generator.py        # IGenerator protocol
│   │   └── chunker.py          # IChunker protocol
│   └── exceptions.py           # Custom exceptions hierarchy
├── ingestion/
│   ├── __init__.py
│   ├── service.py              # IngestionService (orchestrates pipeline)
│   ├── reader.py               # TextReader (file loading)
│   ├── chunker.py              # SentenceChunker (ML-based sentence splitting)
│   └── paragraph_builder.py    # ParagraphBuilder (10-sentence blocks)
├── generation/
│   ├── __init__.py
│   ├── service.py              # GenerationService (orchestrates RAG flow)
│   ├── prompt_builder.py       # PromptBuilder (context-aware prompts)
│   └── response_handler.py     # ResponseHandler (OpenAI format)
├── infrastructure/
│   ├── __init__.py
│   ├── llama_client.py         # LlamaClient (embedding, rerank, generate)
│   └── qdrant_client.py        # QdrantRepository (vector operations)
└── utils/
    ├── __init__.py
    └── batch.py                # Batch processing utilities

var/
└── data/
    └── book.txt                # Le Petit Prince source text

config.yml                      # Default configuration
.env                            # Environment overrides (gitignored)
```

## SOLID Principles Application

- **S (Single Responsibility)**: Each class has one job (Reader reads, Chunker chunks, etc.)
- **O (Open/Closed)**: New chunking strategies via new IChunker implementations
- **L (Liskov Substitution)**: All implementations fully substitute their interfaces
- **I (Interface Segregation)**: Small, focused interfaces (IEmbedder, IReranker, IGenerator)
- **D (Dependency Inversion)**: Services depend on abstractions, not concrete implementations

## Configuration Priority

```
ENV VARIABLES > .env file > config.yml
```

### Configuration Validation

**All configuration fields must be validated at startup. The application must fail fast with explicit error messages.**

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

    @field_validator("base_url")
    @classmethod
    def validate_url_reachable(cls, v: str) -> str:
        # Optionally ping endpoint at startup
        return v

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
        if not v.is_file():
            raise ValueError(f"Source path is not a file: {v}")
        return v
```

### Validation Error Messages

```python
# Bad: generic Pydantic error
ValidationError: 1 validation error for Config

# Good: actionable startup error
ConfigurationError(
    "Invalid configuration in 'retrieval' section",
    context={
        "field": "top_x",
        "value": 50,
        "constraint": "must be <= top_k (20)",
        "suggestion": "Set top_x to a value <= 20, or increase top_k"
    }
)
```

### Startup Validation Sequence

```python
def validate_config_at_startup(config: Settings) -> None:
    """Validate all config values and external dependencies at startup."""
    errors = []

    # 1. Schema validation (Pydantic handles this)

    # 2. File existence
    if not config.ingestion.source_file.exists():
        errors.append(f"Source file not found: {config.ingestion.source_file}")

    # 3. Service connectivity (optional, can be deferred)
    try:
        httpx.get(f"{config.llama.base_url}/health", timeout=5)
    except httpx.RequestError as e:
        errors.append(f"Cannot reach llama.cpp at {config.llama.base_url}: {e}")

    # 4. Logical consistency
    if config.retrieval.top_x > config.retrieval.top_k:
        errors.append("top_x cannot exceed top_k")

    if errors:
        raise ConfigurationError(
            f"Configuration validation failed with {len(errors)} error(s)",
            context={"errors": errors}
        )
```

### config.yml Structure

```yaml
server:
  host: "0.0.0.0"
  port: 8000

llama:
  # Instance 1 : Embedding (ex: Qwen-2.5-1.5B)
  embedding_url: "http://llama-embed:8080"
  embedding_model: "Qwen-Embedding"

  # Instance 2 : Reranking (ex: Qwen-Reranker)
  rerank_url: "http://llama-rerank:8081"
  reranker_model: "Qwen-Reranker"

  # Instance 3 : Generation (ex: DeepSeek-R1-Distill)
  generation_url: "http://llama-gen:8082"
  generation_model: "DeepSeek-R1"

  timeout: 120

qdrant:
  host: "localhost"
  port: 6333
  collection_name: "petit_prince"
  on_disk_payload: true # Store payloads on SSD, not RAM
  distance: "Cosine"

ingestion:
  source_file: "var/data/book.txt"
  sentences_per_paragraph: 10

retrieval:
  top_k: 20 # Initial vector search results
  top_x: 5 # Results after reranking (ALL sent to LLM)
  relevance_threshold: 0.7 # Threshold for [HAUTE] vs [MODÉRÉE] tagging

logging:
  level: "INFO"
  format: "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
```

## Key Implementation Details

### Sentence Chunking (ML-based)

Use lightweight ML model for sentence boundary detection:

```python
# Recommended: pysbd (rule-based + ML) or spacy sentencizer
# Handle imperfect syntax: chapter headers, paragraph numbers
# Filter out: "Chapitre I", "1.", standalone numbers, etc.
```

Pattern to filter:

```python
NOISE_PATTERNS = [
    r"^Chapitre\s+[IVXLCDM]+\.?$",
    r"^\d+\.?$",
    r"^[IVXLCDM]+\.?$",
]
```

#### Robust Chunking Strategy

To effectively index 'The Little Prince', we use a single-sentence and simulated paragraph indexing strategy (10 sentences for example) for stronger search for generation in cases of 'Of course' sentences or dialogue.

### Paragraph Builder Logic

The objective is to capture the context. A single sentence ("Of course.") has no semantic meaning for vector search.

#### Algorithm: Grouping of 10 consecutive sentences.

Overlap: Optional (e.g. 2 sentences).

Metadata: Each chunk keeps the index of the page or chapter if available.

### Noise Filtering (Regex)

The raw text contains artifacts that pollute the embedding. Cleaning must be done before chunking.

```Python
CLEANING_PATTERNS = [
    # Chapter titles (Roman numerals alone or with "Chapter")
    r" (?:Chapter s+)? [IVXLCDM]+ .?  s*$",

    # Page numbers or isolated paragraphs
    r"  d+ .?  s*$",

    # Image indications or editorial metadata
    r [Illustration.*?  ]$",

    # Very short non-dialogued lines (scan noise)
    r" . {1,3}$"
]

def is_noise(sentence: str) -> bool:
    ""Detect if a sentence is structural noise.
    sentence = sentence.strip()
    if not sentence:
        return True
    for pattern in CLEANING_PATTERNS:
        if re.match(pattern, sentence, re.IGNORECASE):
            return True
```

### Embedding with llama.cpp

```python
# POST /v1/embeddings with model swap
{
    "model": "Qwen",
    "input": ["sentence1", "sentence2", ...],
    "encoding_format": "float"
}

# For query embedding with instruction:
{
    "model": "Qwen",
    "input": "Instruct: Given a query, retrieve relevant passages\nQuery: {user_query}",
    "encoding_format": "float"
}
```

### Reranking with llama.cpp

```python
# POST /v1/rerank
{
    "model": "ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF:Q8_0",
    "query": "user question",
    "documents": ["doc1", "doc2", ...],
    "top_n": 5
}
```

### Qdrant Collection Setup

```python
# Create collection with cosine similarity and on-disk payload
client.create_collection(
    collection_name="petit_prince",
    vectors_config=VectorParams(
        size=1024,  # From config
        distance=Distance.COSINE,
        on_disk=True  # Vectors on disk if needed
    ),
    on_disk_payload=True  # Payloads stored on SSD
)
```

### Prompt Building Strategy

**All top_x documents from the reranker are ALWAYS included in the context**, regardless of their score. The system prompt instructs the LLM how to interpret and use them based on relevance assessment.

#### System Prompt Structure

The system prompt has three variants based on document relevance scores relative to the threshold:

---

**Scenario 1: All documents highly relevant** (all scores ≥ threshold)

```
Tu es un expert littéraire spécialisé dans "Le Petit Prince" d'Antoine de Saint-Exupéry. Tu possèdes une connaissance approfondie de l'œuvre, de ses thèmes, de sa symbolique et de son contexte historique.

RÔLE ET IDENTITÉ :
- Tu es un guide bienveillant qui aide à comprendre et apprécier cette œuvre
- Tu t'exprimes avec clarté, précision et une touche de poésie fidèle à l'esprit du livre
- Tu ne prétends jamais être l'auteur ni un personnage du livre

SOURCES À TA DISPOSITION :
Les extraits fournis ci-dessous sont tous hautement pertinents pour répondre à la question. Tu dois :
- T'appuyer principalement sur ces extraits pour construire ta réponse
- Citer ou paraphraser les passages pertinents quand cela enrichit ta réponse
- Rester fidèle au texte original dans tes interprétations

CONTRAINTES DE RÉPONSE :
- Réponds en français, sauf si l'utilisateur écrit dans une autre langue
- Sois concis mais complet : vise 2-4 paragraphes sauf si une réponse plus courte suffit
- Ne commence jamais par "En tant qu'expert..." ou formules similaires
- Si la question dépasse le cadre du Petit Prince, recentre poliment la discussion
- N'invente jamais de citations ou de passages qui ne figurent pas dans les extraits fournis

TON ET STYLE :
- Adopte un ton chaleureux et accessible, jamais condescendant
- Utilise des formulations qui invitent à la réflexion plutôt qu'à l'acceptation passive
- Évite le jargon académique excessif tout en restant précis
```

---

**Scenario 2: Partial relevance** (some scores ≥ threshold, some < threshold)

```
Tu es un expert littéraire spécialisé dans "Le Petit Prince" d'Antoine de Saint-Exupéry. Tu possèdes une connaissance approfondie de l'œuvre, de ses thèmes, de sa symbolique et de son contexte historique.

RÔLE ET IDENTITÉ :
- Tu es un guide bienveillant qui aide à comprendre et apprécier cette œuvre
- Tu t'exprimes avec clarté, précision et une touche de poésie fidèle à l'esprit du livre
- Tu ne prétends jamais être l'auteur ni un personnage du livre

SOURCES À TA DISPOSITION :
Les extraits fournis ci-dessous ont des niveaux de pertinence variables. Chaque extrait est précédé d'un indicateur [PERTINENCE: HAUTE] ou [PERTINENCE: MODÉRÉE].
Tu dois :
- Prioriser les extraits marqués [PERTINENCE: HAUTE] comme sources principales
- Utiliser les extraits [PERTINENCE: MODÉRÉE] comme contexte complémentaire uniquement s'ils apportent une valeur ajoutée
- Signaler si ta réponse repose principalement sur ta connaissance générale plutôt que sur les extraits fournis
- Ne jamais présenter un extrait modérément pertinent comme s'il répondait directement à la question

CONTRAINTES DE RÉPONSE :
- Réponds en français, sauf si l'utilisateur écrit dans une autre langue
- Sois concis mais complet : vise 2-4 paragraphes sauf si une réponse plus courte suffit
- Ne commence jamais par "En tant qu'expert..." ou formules similaires
- Si les extraits ne suffisent pas, complète avec ta connaissance de l'œuvre en le mentionnant
- N'invente jamais de citations ou de passages

TON ET STYLE :
- Adopte un ton chaleureux et accessible, jamais condescendant
- Utilise des formulations qui invitent à la réflexion
- Sois transparent sur le degré de certitude de ta réponse
```

---

**Scenario 3: No highly relevant documents** (all scores < threshold)

```
Tu es un expert littéraire spécialisé dans "Le Petit Prince" d'Antoine de Saint-Exupéry. Tu possèdes une connaissance approfondie de l'œuvre, de ses thèmes, de sa symbolique et de son contexte historique.

RÔLE ET IDENTITÉ :
- Tu es un guide bienveillant qui aide à comprendre et apprécier cette œuvre
- Tu t'exprimes avec clarté, précision et une touche de poésie fidèle à l'esprit du livre
- Tu ne prétends jamais être l'auteur ni un personnage du livre

SOURCES À TA DISPOSITION :
Les extraits fournis ci-dessous ont une pertinence limitée par rapport à la question posée. Ils sont fournis comme contexte général mais ne répondent pas directement à la question.
Tu dois :
- Te baser principalement sur ta connaissance générale du Petit Prince pour répondre
- Mentionner explicitement que tu ne disposes pas d'extrait directement pertinent
- Utiliser les extraits uniquement s'ils apportent un éclairage indirect utile
- Proposer de reformuler la question si elle semble hors sujet ou ambiguë

CONTRAINTES DE RÉPONSE :
- Réponds en français, sauf si l'utilisateur écrit dans une autre langue
- Sois honnête sur les limites de ta réponse : précise qu'elle repose sur ta connaissance générale
- Si la question porte sur un élément très spécifique du texte que tu ne peux pas vérifier, dis-le
- N'invente jamais de citations ; si tu paraphrases de mémoire, indique-le clairement
- Si la question est hors sujet (pas liée au Petit Prince), explique poliment ton périmètre

TON ET STYLE :
- Reste utile et constructif malgré l'absence d'extraits pertinents
- Propose des pistes de réflexion ou des questions connexes que tu pourrais mieux traiter
- Adopte un ton humble sans être excessivement apologétique
```

---

#### Context Injection Format

All documents are injected into the **last user message**, after the original query:

```python
def build_user_message_with_context(
    original_query: str,
    documents: list[RankedDocument],
    threshold: float
) -> str:
    """Build the final user message with all documents injected."""

    context_parts = []
    for i, doc in enumerate(documents, 1):
        if doc.score >= threshold:
            relevance_tag = "[PERTINENCE: HAUTE]"
        else:
            relevance_tag = "[PERTINENCE: MODÉRÉE]"

        context_parts.append(f"--- Extrait {i} {relevance_tag} ---\n{doc.text}")

    context_block = "\n\n".join(context_parts)

    return f"""{original_query}

---
EXTRAITS DU PETIT PRINCE POUR CONTEXTE :

{context_block}
---"""
```

#### Final Prompt Assembly

```python
def build_final_messages(
    conversation: list[Message],
    documents: list[RankedDocument],
    threshold: float
) -> list[dict]:
    """Assemble the complete message list for the LLM."""

    # 1. Determine system prompt variant
    scores = [doc.score for doc in documents]
    if all(s >= threshold for s in scores):
        system_prompt = SYSTEM_PROMPT_ALL_RELEVANT
    elif any(s >= threshold for s in scores):
        system_prompt = SYSTEM_PROMPT_PARTIAL
    else:
        system_prompt = SYSTEM_PROMPT_LOW_RELEVANCE

    # 2. Build messages array
    messages = [{"role": "system", "content": system_prompt}]

    # 3. Add conversation history (all but last message)
    for msg in conversation[:-1]:
        messages.append({"role": msg.role, "content": msg.content})

    # 4. Add last user message WITH context injected
    last_user_msg = conversation[-1]
    augmented_content = build_user_message_with_context(
        original_query=last_user_msg.content,
        documents=documents,
        threshold=threshold
    )
    messages.append({"role": "user", "content": augmented_content})

    return messages
```

#### Example Output

For a query "Qui est le renard et que représente-t-il?" with partial relevance:

```json
[
  {
    "role": "system",
    "content": "Tu es un expert littéraire spécialisé dans \"Le Petit Prince\"..."
  },
  {
    "role": "user",
    "content": "Bonjour, j'aimerais comprendre le livre"
  },
  {
    "role": "assistant",
    "content": "Bonjour ! Je serai ravi de vous accompagner..."
  },
  {
    "role": "user",
    "content": "Qui est le renard et que représente-t-il?\n\n---\nEXTRAITS DU PETIT PRINCE POUR CONTEXTE :\n\n--- Extrait 1 [PERTINENCE: HAUTE] ---\n\"On ne connaît que les choses que l'on apprivoise, dit le renard. Les hommes n'ont plus le temps de rien connaître. Ils achètent des choses toutes faites chez les marchands.\"\n\n--- Extrait 2 [PERTINENCE: HAUTE] ---\n\"Tu deviens responsable pour toujours de ce que tu as apprivoisé. Tu es responsable de ta rose...\"\n\n--- Extrait 3 [PERTINENCE: MODÉRÉE] ---\nLe petit prince s'en fut revoir les roses : \"Vous n'êtes pas du tout semblables à ma rose, vous n'êtes rien encore, leur dit-il.\"\n\n--- Extrait 4 [PERTINENCE: MODÉRÉE] ---\nC'est alors qu'apparut le renard.\n\n--- Extrait 5 [PERTINENCE: MODÉRÉE] ---\n\"Les hommes, dit le renard, ils ont des fusils et ils chassent.\"\n---"
  }
]
```

### Empty index search or reranking

The non-reporting by index search or reranking (error or other - not a score under the thresold) of documents is properly managed

### OpenAI-Compatible Chat Format

Request:

```json
{
  "model": "petit-prince-rag",
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "Qui est le renard?" },
    { "role": "assistant", "content": "..." },
    { "role": "user", "content": "Et que lui apprend-il?" }
  ],
  "stream": false
}
```

Response:

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
  "usage": { "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0 }
}
```

## Logging Guidelines

Format: `timestamp | LEVEL | module:function:line | message`

Levels:

- **DEBUG**: Batch progress, vector dimensions, raw scores
- **INFO**: Pipeline stages, API calls, indexation progress
- **WARNING**: Low relevance scores, retry attempts, fallbacks
- **ERROR**: API failures, parsing errors, connection issues
- **CRITICAL**: Service unavailable, data corruption

Examples:

```python
logger.info("Starting ingestion from %s", config.source_file)
logger.debug("Chunked into %d sentences, %d paragraphs", n_sent, n_para)
logger.warning("Reranker returned no documents above threshold %.2f", threshold)
logger.error("Qdrant connection failed: %s", str(e))
```

## Docstrings (Google Style)

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

## Comments Policy

- **Do**: Explain complex regex, non-obvious business rules, workarounds
- **Don't**: Comment obvious code, restate function names, add noise

```python
# Good: Explain WHY
# Filter chapter headers that pysbd incorrectly identifies as sentences
if CHAPTER_PATTERN.match(sentence):
    continue

# Bad: Restate WHAT
# Loop through sentences
for sentence in sentences:
```

## API Endpoints

| Method | Path                       | Description                                            |
| ------ | -------------------------- | ------------------------------------------------------ |
| POST   | `/api/init`                | Destroy existing collection, re-index book.txt         |
| POST   | `/api/v1/chat/completions` | OpenAI-compatible chat (supports `stream: true/false`) |
| GET    | `/health`                  | Service health check                                   |
| GET    | `/metrics`                 | Prometheus-style metrics (optional)                    |

## User Interface (Frontend)

A lightweight, single-page web interface for interacting with the RAG pipeline. **Zero business logic** - all intelligence remains in the API. The frontend is purely presentational with API communication logic.

### Design Philosophy

- **Minimalist**: Single HTML file with inline CSS, single JS file
- **Zero dependencies**: No frameworks (React/Vue), no build step, no npm
- **Accessible**: Semantic HTML, keyboard navigation, screen reader friendly
- **Responsive**: Works on mobile, tablet, desktop
- **Progressive**: Works without JavaScript (displays message to enable it)

### Frontend Architecture

```
src/
frontend/
├── index.html              # Complete UI structure with inline CSS
├── app.js                  # API communication + DOM manipulation
└── assets/
    └── favicon.svg         # (Optional) Le Petit Prince themed icon
```

**Nginx serves static files** - see Docker Compose section for configuration.

---

## Frontend Functional Requirements

### 1. Core Chat Interface

#### Layout Structure

```
┌─────────────────────────────────────────┐
│  Le Petit Prince - Assistant Littéraire │  ← Header
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 👤 User: Qui est le renard?    │   │  ← User message
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ 🤖 Assistant: Le renard est...  │   │  ← Assistant message
│  │                                 │   │
│  │ [SOURCES] [METRICS] (debug)     │   │  ← Optional debug info
│  └─────────────────────────────────┘   │
│                                         │
│  ⏳ Génération en cours...             │  ← Streaming indicator
│                                         │
├─────────────────────────────────────────┤
│ [ Votre question ici... ]  [Envoyer]    │  ← Input area
│ ☐ Mode Debug    🗑️ Effacer             │  ← Controls
└─────────────────────────────────────────┘
```

#### Message Types

**User Message**
- Avatar/icon indicator
- Text content
- Timestamp (HH:MM)
- Right-aligned styling

**Assistant Message**
- Avatar/icon indicator (book or character)
- Streaming content (token-by-token)
- Timestamp (HH:MM)
- Left-aligned styling
- Optional expandable sections:
  - 📚 **Sources** (retrieved extracts with relevance tags)
  - 📊 **Metrics** (timing, tokens, scores)

**System Message** (optional)
- Centered, muted styling
- For initialization, errors, notifications

### 2. Debug Mode Toggle

**Purpose**: Display internal RAG pipeline information for transparency and debugging.

**Behavior**:
- Checkbox in footer: `☐ Mode Debug`
- Persisted in `localStorage`
- When enabled, each assistant message shows collapsible sections:

**Debug Information Display**:

```
🤖 Le renard est un personnage qui enseigne au Petit Prince...

┌─ 📚 SOURCES (5 extraits) ─────────────────┐  ← Collapsible
│ Extrait 1 [PERTINENCE: HAUTE - 0.92]      │
│ "On ne connaît que les choses..."         │
│                                            │
│ Extrait 2 [PERTINENCE: HAUTE - 0.87]      │
│ "Tu deviens responsable..."                │
│                                            │
│ ... (3 more)                               │
└────────────────────────────────────────────┘

┌─ 📊 MÉTRIQUES ────────────────────────────┐  ← Collapsible
│ Temps total: 2.50s                         │
│   - Embedding: 45ms                        │
│   - Recherche: 12ms                        │
│   - Reranking: 89ms                        │
│   - Génération: 2340ms                     │
│                                            │
│ Tokens:                                    │
│   - Prompt: 1847 tokens                    │
│   - Réponse: 234 tokens                    │
│   - Total: 2081 tokens                     │
│                                            │
│ Documents récupérés: 20 → 5 (reranked)    │
│ Documents au-dessus du seuil: 3/5          │
└────────────────────────────────────────────┘
```

**Implementation**:
- Send `X-Include-Metrics: true` header when debug mode enabled
- Parse `x_metrics` field from API response
- Render in expandable `<details>` elements

### 3. Streaming Experience

**Visual States**:

1. **Idle**: Input enabled, send button active
2. **Sending**: Input disabled, button shows spinner
3. **Streaming**:
   - Message appears immediately with empty content
   - Tokens append in real-time (smooth, no flicker)
   - Typing indicator cursor: `▊` at end of content
   - Auto-scroll to bottom as content grows
4. **Complete**: Remove typing cursor, enable input

**Error Handling During Stream**:
- Connection lost: Show "⚠️ Connexion interrompue" in message
- Malformed chunk: Log error, continue with next chunk
- Timeout: Show retry button

### 4. Error Handling & User Feedback

**Error Types & UI Treatment**:

| Error Code | Display                                  | Action                    |
|------------|------------------------------------------|---------------------------|
| 400        | Toast: "Question invalide"               | Clear input, focus        |
| 422        | Toast: "Format de message incorrect"     | Show validation hint      |
| 429        | Toast: "Trop de requêtes, patientez..."  | Disable for `Retry-After` |
| 500        | Toast: "Erreur serveur, réessayez"       | Enable retry button       |
| 503        | Toast: "Service indisponible"            | Show retry countdown      |
| Network    | Toast: "Connexion perdue"                | Auto-retry 3x             |

**Toast Notification System**:
- Non-blocking, top-right corner
- Auto-dismiss after 5s (or user click)
- Color-coded: red (error), yellow (warning), green (success)
- No external libraries - pure CSS animations

### 5. Conversation Management

**Actions**:
- 🗑️ **Clear Chat**: Erase conversation history
  - Confirm dialog: "Effacer toute la conversation ?"
  - Clears localStorage and UI

- 💾 **Export** (optional future enhancement):
  - Download conversation as JSON or Markdown

**Conversation Persistence**:
- Store messages in `localStorage` as JSON array
- Restore on page load
- Structure: `{role: "user"|"assistant", content: string, timestamp: number, metrics?: object}`

### 6. Initialization Flow

**On Page Load**:

1. Check API health: `GET /health`
   - ✅ Healthy: Enable chat
   - ❌ Unhealthy: Show banner "Service en démarrage..."

2. Check if index exists (detect via first API call)
   - If 400 with "collection not initialized":
     - Show button "📥 Initialiser l'index"
     - On click: `POST /api/init` with progress indicator

3. Restore conversation from localStorage

4. Focus on input field

---

## Complete Implementation

### index.html

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Le Petit Prince - Assistant Littéraire</title>
    <style>
        /* ===== CSS Reset & Base ===== */
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
            --primary: #4A90E2;
            --primary-dark: #2E5C8A;
            --secondary: #F5A623;
            --bg-light: #F8F9FA;
            --bg-white: #FFFFFF;
            --text-dark: #2C3E50;
            --text-muted: #6C757D;
            --border: #DEE2E6;
            --error: #E74C3C;
            --success: #27AE60;
            --warning: #F39C12;
            --shadow: rgba(0, 0, 0, 0.1);
            --font-main: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
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

        /* ===== Main Container ===== */
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

        /* ===== Header ===== */
        .header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 1.5rem;
            text-align: center;
            border-bottom: 3px solid var(--secondary);
        }

        .header h1 {
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }

        .header p {
            font-size: 0.9rem;
            opacity: 0.9;
        }

        /* ===== Chat Area ===== */
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
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
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
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .message.user .message-content {
            background: var(--primary);
            color: white;
        }

        .message-text {
            margin: 0;
            word-wrap: break-word;
        }

        .message-timestamp {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 0.5rem;
            display: block;
        }

        .message.user .message-timestamp {
            color: rgba(255,255,255,0.8);
        }

        /* Typing indicator */
        .typing-cursor {
            display: inline-block;
            width: 2px;
            height: 1em;
            background: var(--text-dark);
            margin-left: 2px;
            animation: blink 1s infinite;
        }

        @keyframes blink {
            0%, 49% { opacity: 1; }
            50%, 100% { opacity: 0; }
        }

        /* ===== Debug Sections ===== */
        .debug-section {
            margin-top: 1rem;
            border-top: 1px solid var(--border);
            padding-top: 1rem;
        }

        .debug-section summary {
            cursor: pointer;
            font-weight: 600;
            color: var(--primary);
            user-select: none;
            margin-bottom: 0.5rem;
        }

        .debug-section summary:hover {
            color: var(--primary-dark);
        }

        .debug-content {
            font-family: var(--font-mono);
            font-size: 0.85rem;
            background: var(--bg-light);
            padding: 0.75rem;
            border-radius: 6px;
            margin-top: 0.5rem;
        }

        .source-item {
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }

        .source-item:last-child {
            border-bottom: none;
        }

        .source-tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-left: 0.5rem;
        }

        .source-tag.high {
            background: #d4edda;
            color: #155724;
        }

        .source-tag.moderate {
            background: #fff3cd;
            color: #856404;
        }

        .metric-row {
            display: flex;
            justify-content: space-between;
            padding: 0.25rem 0;
        }

        .metric-label {
            color: var(--text-muted);
        }

        .metric-value {
            font-weight: 600;
        }

        /* ===== Loading Indicator ===== */
        .loading-message {
            text-align: center;
            color: var(--text-muted);
            font-style: italic;
            padding: 1rem;
            animation: pulse 1.5s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
        }

        /* ===== Input Area ===== */
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
            font-family: var(--font-main);
            transition: border-color 0.2s;
        }

        .input-field:focus {
            outline: none;
            border-color: var(--primary);
        }

        .input-field:disabled {
            background: var(--bg-light);
            cursor: not-allowed;
        }

        .send-button {
            padding: 0.75rem 1.5rem;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }

        .send-button:hover:not(:disabled) {
            background: var(--primary-dark);
        }

        .send-button:disabled {
            background: var(--text-muted);
            cursor: not-allowed;
        }

        .controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .checkbox-wrapper {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            cursor: pointer;
        }

        .checkbox-wrapper input {
            cursor: pointer;
        }

        .clear-button {
            background: none;
            border: none;
            color: var(--error);
            cursor: pointer;
            font-size: 0.9rem;
            padding: 0.5rem;
            transition: color 0.2s;
        }

        .clear-button:hover {
            color: #c0392b;
        }

        /* ===== Toast Notifications ===== */
        .toast-container {
            position: fixed;
            top: 2rem;
            right: 2rem;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .toast {
            min-width: 300px;
            padding: 1rem 1.25rem;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px var(--shadow);
            animation: slideIn 0.3s ease-out;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        .toast.error { border-left: 4px solid var(--error); }
        .toast.success { border-left: 4px solid var(--success); }
        .toast.warning { border-left: 4px solid var(--warning); }

        .toast-icon {
            font-size: 1.5rem;
        }

        .toast-message {
            flex: 1;
        }

        /* ===== Initialization Banner ===== */
        .init-banner {
            background: var(--warning);
            color: white;
            padding: 1rem;
            text-align: center;
            display: none;
        }

        .init-banner.show {
            display: block;
        }

        .init-button {
            background: white;
            color: var(--warning);
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 0.5rem;
        }

        /* ===== Responsive ===== */
        @media (max-width: 768px) {
            .container {
                max-height: 100vh;
                height: 100vh;
                border-radius: 0;
            }

            .message-content {
                max-width: 85%;
            }

            .header h1 {
                font-size: 1.25rem;
            }
        }

        /* ===== Accessibility ===== */
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border-width: 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <h1>Le Petit Prince - Assistant Littéraire</h1>
            <p>Explorez l'œuvre d'Antoine de Saint-Exupéry avec l'aide de l'IA</p>
        </header>

        <!-- Initialization Banner (hidden by default) -->
        <div id="initBanner" class="init-banner">
            <p>⚠️ L'index n'est pas encore initialisé</p>
            <button id="initButton" class="init-button">📥 Initialiser l'index</button>
        </div>

        <!-- Chat Container -->
        <main id="chatContainer" class="chat-container" role="log" aria-live="polite" aria-atomic="false">
            <!-- Messages will be inserted here dynamically -->
        </main>

        <!-- Input Area -->
        <div class="input-area">
            <div class="input-wrapper">
                <input
                    type="text"
                    id="messageInput"
                    class="input-field"
                    placeholder="Posez votre question sur Le Petit Prince..."
                    aria-label="Champ de question"
                    autocomplete="off"
                >
                <button id="sendButton" class="send-button" aria-label="Envoyer">
                    Envoyer
                </button>
            </div>
            <div class="controls">
                <label class="checkbox-wrapper">
                    <input type="checkbox" id="debugToggle" aria-label="Mode debug">
                    <span>Mode Debug</span>
                </label>
                <button id="clearButton" class="clear-button" aria-label="Effacer la conversation">
                    🗑️ Effacer
                </button>
            </div>
        </div>
    </div>

    <!-- Toast Container -->
    <div id="toastContainer" class="toast-container" role="status" aria-live="polite"></div>

    <script src="app.js"></script>
</body>
</html>
```

### app.js

```javascript
/**
 * Le Petit Prince RAG Frontend
 * Pure vanilla JavaScript - no dependencies
 */

// ===== Configuration =====
const CONFIG = {
    API_BASE_URL: window.location.origin,
    ENDPOINTS: {
        CHAT: '/api/v1/chat/completions',
        INIT: '/api/init',
        HEALTH: '/health'
    },
    STORAGE_KEYS: {
        CONVERSATION: 'lpp_conversation',
        DEBUG_MODE: 'lpp_debug_mode'
    },
    TOAST_DURATION: 5000,
    MAX_RETRIES: 3
};

// ===== State Management =====
const state = {
    conversation: [],
    debugMode: false,
    isStreaming: false,
    currentMessageId: null
};

// ===== DOM Elements =====
const elements = {
    chatContainer: document.getElementById('chatContainer'),
    messageInput: document.getElementById('messageInput'),
    sendButton: document.getElementById('sendButton'),
    debugToggle: document.getElementById('debugToggle'),
    clearButton: document.getElementById('clearButton'),
    initBanner: document.getElementById('initBanner'),
    initButton: document.getElementById('initButton'),
    toastContainer: document.getElementById('toastContainer')
};

// ===== Initialization =====
function init() {
    loadDebugMode();
    loadConversation();
    checkAPIHealth();
    attachEventListeners();
    focusInput();
}

function attachEventListeners() {
    // Send message on button click
    elements.sendButton.addEventListener('click', handleSendMessage);

    // Send message on Enter key
    elements.messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });

    // Debug mode toggle
    elements.debugToggle.addEventListener('change', handleDebugToggle);

    // Clear conversation
    elements.clearButton.addEventListener('click', handleClearConversation);

    // Initialize index
    elements.initButton.addEventListener('click', handleInitIndex);
}

// ===== API Health Check =====
async function checkAPIHealth() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.HEALTH}`);
        if (!response.ok) {
            showToast('Service indisponible', 'error');
        }
    } catch (error) {
        showToast('Impossible de contacter le serveur', 'error');
        console.error('Health check failed:', error);
    }
}

// ===== Message Handling =====
async function handleSendMessage() {
    const text = elements.messageInput.value.trim();

    if (!text || state.isStreaming) return;

    // Add user message to conversation
    const userMessage = {
        role: 'user',
        content: text,
        timestamp: Date.now()
    };

    addMessageToConversation(userMessage);
    renderMessage(userMessage);

    // Clear input and disable
    elements.messageInput.value = '';
    setInputState(false);

    // Send to API
    await sendMessageToAPI();
}

async function sendMessageToAPI() {
    state.isStreaming = true;

    // Prepare messages for API
    const messages = state.conversation.map(msg => ({
        role: msg.role,
        content: msg.content
    }));

    const headers = {
        'Content-Type': 'application/json'
    };

    // Add metrics header if debug mode enabled
    if (state.debugMode) {
        headers['X-Include-Metrics'] = 'true';
    }

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.CHAT}`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
                model: 'petit-prince-rag',
                messages,
                stream: true
            })
        });

        if (!response.ok) {
            await handleAPIError(response);
            return;
        }

        await handleStreamingResponse(response);

    } catch (error) {
        handleNetworkError(error);
    } finally {
        state.isStreaming = false;
        setInputState(true);
        focusInput();
    }
}

async function handleStreamingResponse(response) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    // Create assistant message placeholder
    const assistantMessage = {
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
        metrics: null
    };

    state.currentMessageId = addMessageToConversation(assistantMessage);
    const messageElement = renderMessage(assistantMessage, true);
    const contentElement = messageElement.querySelector('.message-text');

    let buffer = '';

    try {
        while (true) {
            const { done, value } = await reader.read();

            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');

            // Keep last incomplete line in buffer
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (!line.trim() || !line.startsWith('data: ')) continue;

                const data = line.slice(6); // Remove 'data: ' prefix

                if (data === '[DONE]') {
                    removeTypingCursor(contentElement);
                    saveConversation();
                    continue;
                }

                try {
                    const chunk = JSON.parse(data);

                    // Handle content delta
                    if (chunk.choices?.[0]?.delta?.content) {
                        const token = chunk.choices[0].delta.content;
                        assistantMessage.content += token;
                        updateMessageContent(contentElement, assistantMessage.content, true);
                        scrollToBottom();
                    }

                    // Handle usage/metrics in final chunk
                    if (chunk.usage) {
                        assistantMessage.metrics = {
                            usage: chunk.usage,
                            ...(chunk.x_metrics || {})
                        };

                        if (state.debugMode) {
                            renderDebugInfo(messageElement, assistantMessage.metrics);
                        }
                    }

                } catch (parseError) {
                    console.error('Failed to parse chunk:', parseError);
                }
            }
        }

    } catch (streamError) {
        console.error('Stream error:', streamError);
        showToast('Connexion interrompue', 'error');
        contentElement.innerHTML += '<br><span style="color: var(--error);">⚠️ Connexion interrompue</span>';
    }
}

async function handleAPIError(response) {
    const errorData = await response.json().catch(() => ({}));
    const errorMessage = errorData.error?.message || 'Erreur inconnue';

    switch (response.status) {
        case 400:
            if (errorMessage.includes('init') || errorMessage.includes('collection')) {
                elements.initBanner.classList.add('show');
            }
            showToast(errorMessage, 'error');
            break;
        case 422:
            showToast('Format de message incorrect', 'error');
            break;
        case 429:
            showToast('Trop de requêtes, veuillez patienter...', 'warning');
            break;
        case 503:
            showToast('Service indisponible, réessayez plus tard', 'error');
            break;
        default:
            showToast('Erreur serveur', 'error');
    }
}

function handleNetworkError(error) {
    console.error('Network error:', error);
    showToast('Connexion perdue', 'error');
}

// ===== Index Initialization =====
async function handleInitIndex() {
    elements.initButton.disabled = true;
    elements.initButton.textContent = '⏳ Initialisation...';

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.INIT}`, {
            method: 'POST'
        });

        if (response.ok) {
            showToast('Index initialisé avec succès', 'success');
            elements.initBanner.classList.remove('show');
        } else {
            const error = await response.json();
            showToast(error.error?.message || 'Échec de l\'initialisation', 'error');
        }

    } catch (error) {
        showToast('Erreur réseau', 'error');
    } finally {
        elements.initButton.disabled = false;
        elements.initButton.textContent = '📥 Initialiser l\'index';
    }
}

// ===== Rendering Functions =====
function renderMessage(message, isStreaming = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${message.role}`;
    messageDiv.setAttribute('data-message-id', state.conversation.length - 1);

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = message.role === 'user' ? '👤' : '📖';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const textP = document.createElement('p');
    textP.className = 'message-text';
    updateMessageContent(textP, message.content, isStreaming);

    const timestamp = document.createElement('small');
    timestamp.className = 'message-timestamp';
    timestamp.textContent = formatTimestamp(message.timestamp);

    contentDiv.appendChild(textP);
    contentDiv.appendChild(timestamp);

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);

    elements.chatContainer.appendChild(messageDiv);
    scrollToBottom();

    return messageDiv;
}

function updateMessageContent(element, content, showCursor = false) {
    element.textContent = content;

    if (showCursor) {
        const cursor = document.createElement('span');
        cursor.className = 'typing-cursor';
        element.appendChild(cursor);
    }
}

function removeTypingCursor(element) {
    const cursor = element.querySelector('.typing-cursor');
    if (cursor) cursor.remove();
}

function renderDebugInfo(messageElement, metrics) {
    const contentDiv = messageElement.querySelector('.message-content');

    // Sources section
    if (metrics.retrieval?.documents) {
        const sourcesDetails = document.createElement('details');
        sourcesDetails.className = 'debug-section';

        const sourcesSummary = document.createElement('summary');
        sourcesSummary.textContent = `📚 SOURCES (${metrics.retrieval.documents.length} extraits)`;

        const sourcesContent = document.createElement('div');
        sourcesContent.className = 'debug-content';

        metrics.retrieval.documents.forEach((doc, index) => {
            const sourceItem = document.createElement('div');
            sourceItem.className = 'source-item';

            const isHigh = doc.score >= (metrics.retrieval.threshold_used || 0.7);
            const tag = `<span class="source-tag ${isHigh ? 'high' : 'moderate'}">${isHigh ? 'HAUTE' : 'MODÉRÉE'} - ${doc.score.toFixed(2)}</span>`;

            sourceItem.innerHTML = `
                <strong>Extrait ${index + 1}</strong> ${tag}
                <p style="margin-top: 0.5rem; color: var(--text-dark);">${doc.text.substring(0, 200)}${doc.text.length > 200 ? '...' : ''}</p>
            `;

            sourcesContent.appendChild(sourceItem);
        });

        sourcesDetails.appendChild(sourcesSummary);
        sourcesDetails.appendChild(sourcesContent);
        contentDiv.appendChild(sourcesDetails);
    }

    // Metrics section
    const metricsDetails = document.createElement('details');
    metricsDetails.className = 'debug-section';

    const metricsSummary = document.createElement('summary');
    metricsSummary.textContent = '📊 MÉTRIQUES';

    const metricsContent = document.createElement('div');
    metricsContent.className = 'debug-content';

    const timings = metrics.timings || {};
    const usage = metrics.usage || {};

    metricsContent.innerHTML = `
        <div class="metric-row">
            <span class="metric-label">Temps total:</span>
            <span class="metric-value">${timings.total_ms ? (timings.total_ms / 1000).toFixed(2) + 's' : 'N/A'}</span>
        </div>
        ${timings.embedding_ms ? `<div class="metric-row"><span class="metric-label">  - Embedding:</span><span class="metric-value">${timings.embedding_ms}ms</span></div>` : ''}
        ${timings.search_ms ? `<div class="metric-row"><span class="metric-label">  - Recherche:</span><span class="metric-value">${timings.search_ms}ms</span></div>` : ''}
        ${timings.rerank_ms ? `<div class="metric-row"><span class="metric-label">  - Reranking:</span><span class="metric-value">${timings.rerank_ms}ms</span></div>` : ''}
        ${timings.generation_ms ? `<div class="metric-row"><span class="metric-label">  - Génération:</span><span class="metric-value">${timings.generation_ms}ms</span></div>` : ''}
        <div class="metric-row" style="margin-top: 1rem;">
            <span class="metric-label">Tokens prompt:</span>
            <span class="metric-value">${usage.prompt_tokens || 'N/A'}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Tokens réponse:</span>
            <span class="metric-value">${usage.completion_tokens || 'N/A'}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Total tokens:</span>
            <span class="metric-value">${usage.total_tokens || 'N/A'}</span>
        </div>
    `;

    metricsDetails.appendChild(metricsSummary);
    metricsDetails.appendChild(metricsContent);
    contentDiv.appendChild(metricsDetails);
}

// ===== Conversation Management =====
function addMessageToConversation(message) {
    state.conversation.push(message);
    saveConversation();
    return state.conversation.length - 1;
}

function loadConversation() {
    const stored = localStorage.getItem(CONFIG.STORAGE_KEYS.CONVERSATION);
    if (stored) {
        try {
            state.conversation = JSON.parse(stored);
            state.conversation.forEach(msg => renderMessage(msg));
        } catch (error) {
            console.error('Failed to load conversation:', error);
        }
    }
}

function saveConversation() {
    try {
        localStorage.setItem(
            CONFIG.STORAGE_KEYS.CONVERSATION,
            JSON.stringify(state.conversation)
        );
    } catch (error) {
        console.error('Failed to save conversation:', error);
    }
}

function handleClearConversation() {
    if (!confirm('Effacer toute la conversation ?')) return;

    state.conversation = [];
    elements.chatContainer.innerHTML = '';
    saveConversation();
    showToast('Conversation effacée', 'success');
}

// ===== Debug Mode =====
function loadDebugMode() {
    const stored = localStorage.getItem(CONFIG.STORAGE_KEYS.DEBUG_MODE);
    state.debugMode = stored === 'true';
    elements.debugToggle.checked = state.debugMode;
}

function handleDebugToggle(event) {
    state.debugMode = event.target.checked;
    localStorage.setItem(CONFIG.STORAGE_KEYS.DEBUG_MODE, state.debugMode);
}

// ===== UI Utilities =====
function setInputState(enabled) {
    elements.messageInput.disabled = !enabled;
    elements.sendButton.disabled = !enabled;
    elements.sendButton.textContent = enabled ? 'Envoyer' : '⏳';
}

function focusInput() {
    elements.messageInput.focus();
}

function scrollToBottom() {
    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

// ===== Toast Notifications =====
function showToast(message, type = 'error') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        error: '❌',
        success: '✅',
        warning: '⚠️'
    };

    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-message">${message}</span>
    `;

    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, CONFIG.TOAST_DURATION);
}

// ===== Initialize Application =====
document.addEventListener('DOMContentLoaded', init);
```

---

## Frontend Deployment

### Nginx Configuration

**File**: `config/nginx.conf`

```nginx
server {
    listen 80;
    server_name localhost;

    # Frontend static files
    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
    }

    # API proxy
    location /api/ {
        proxy_pass http://api:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Streaming support
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        chunked_transfer_encoding on;
    }

    # Health check
    location /health {
        proxy_pass http://api:8000/health;
    }

    # Caching for static assets
    location ~* \.(css|js|jpg|jpeg|png|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Docker Compose Integration

Update the `frontend` service in `docker-compose.yml`:

```yaml
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
  healthcheck:
    test: ["CMD-SHELL", "wget -q --spider http://localhost:80/ || exit 1"]
    interval: 30s
    timeout: 5s
    retries: 3
```

---

## Frontend Testing

### Manual Testing Checklist

- [ ] **Streaming**: Tokens appear smoothly without flickering
- [ ] **Debug mode**: Sources and metrics display correctly
- [ ] **Error handling**: Toasts appear for all error scenarios
- [ ] **Persistence**: Conversation survives page refresh
- [ ] **Responsive**: Works on mobile (320px), tablet (768px), desktop (1920px)
- [ ] **Accessibility**: Keyboard navigation works (Tab, Enter, Escape)
- [ ] **Initialization**: Banner shows when index not ready
- [ ] **Network resilience**: Handles disconnections gracefully

### Browser Compatibility

- ✅ Chrome/Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

---

## Future Enhancements (Optional)

1. **Export conversation**: Download as JSON or Markdown
2. **Theme toggle**: Light/dark mode
3. **Voice input**: Speech-to-text for questions
4. **Favorites**: Bookmark interesting Q&A pairs
5. **Search history**: Find previous questions
6. **Multi-language**: English interface option

## Dependencies

```
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
httpx>=0.26.0
qdrant-client>=1.7.0
pysbd>=0.3.4              # Sentence boundary detection
python-dotenv>=1.0.0
pyyaml>=6.0.1
```

## Commands

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
  -H "Content-Type: application/json" \
  -N \
  -d '{"messages": [{"role": "user", "content": "Qui est le petit prince?"}], "stream": true}'

# Chat with extended metrics
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Include-Metrics: true" \
  -d '{"messages": [{"role": "user", "content": "Qui est le petit prince?"}]}'
```

## Environment Variables

All config.yml values can be overridden with env vars using prefix and underscore notation:

```bash
LLAMA_BASE_URL=http://gpu-server:8080
LLAMA_EMBEDDING_DIM=768
QDRANT_HOST=qdrant-server
RETRIEVAL_TOP_K=30
LOGGING_LEVEL=DEBUG
```

## Deployment & Infrastructure (Docker Compose)

The application is containerized via 6 orchestrated services. We use Docker Profiles to handle hardware acceleration (CPU vs. GPU vs. MPS).

### File structure

    - `Dockerfile.api` : Python 3.11 slim + poetry/pip.
    - `Dockerfile.front` : Nginx alpine serving static files.
    - `compose.yml` : Full orchestration.

### compose.yml Optimized

```YAML
services:
  # 1. Vector Database
  qdrant:
    image: qdrant/qdrant:latest
    container_name: little prince-qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 10s
      retries: 5

  # 2. Llama Server - Embedding
  llama-embed:
    image: ghcr.io/ggerganov/llama.cpp:server
    container_name: petit-prince-embed
    profiles: ["cpu", "gpu", "mps"]
    command: -m /models/embed.gguf --embedding --port 8080 --host 0.0.0.0 -cb
    volumes:
      - . /var/models:/models
    deploy: &deploy_config
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capacités : [gpu]

  # 3. Llama Server - Reranking
  llama-rerank:
    image : ghcr.io/ggerganov/llama.cpp:server
    container_name : petit-prince-rerank
    profiles : ["cpu", "gpu", "mps"]
    # Remarque : Utilisation de l’intégration du endpoint ou du répertoire spécifique selon la version
    commande : -m /models/rerank.gguf --reranking --port 8081 --host 0.0.0.0 -cb
    volumes :
      - . /var/models:/models
    deploy : *deploy_config

  # 4. Llama Server - Génération
  llama-gen:
    image : ghcr.io/ggerganov/llama.cpp:server
    container_name : petit-prince-gen
    profiles : ["cpu", "gpu", "mps"]
    commande : -m /models/gen.gguf -c 4096 -ngl 99 --port 8082 --host 0.0.0.0
    volumes :
      - . /var/models:/models
    deploy : *deploy_config

  # 5. Backend API
  api:
    build:
      contexte : .
      dockerfile : Dockerfile.api
    container_name : petit-prince-api
    environnement :
      - QDRANT_HOST=qdrant
      - LLAMA_EMBEDDING_URL=http://llama-embed:8080
      - LLAMA_RERANK_URL=http://llama-rerank:8081
      - LLAMA_GENERATION_URL=http://llama-gen:8082
    depends_on:
      qdrant:
        condition : service_sain
      llama-embed :
        condition : service_started
    ports :
      - "8000:8000"

  # 6. Interface Frontend
  frontend:
    image : nginx:alpine
    container_name : petit-prince-front
    volumes :
      - . /src/frontend:/usr/share/nginx/html
      - . /config/nginx.conf:/etc/nginx/conf. d/default.conf
    ports :
      - "80:80"
    depends_on:
      - api

volumes :
  qdrant_data:
```

### Commandes de Lancement

```Bash
# Profil CPU (Mac Intel / Linux sans GPU)
docker compose --profile cpu up -d

# Profil GPU (Linux + Nvidia)
docker compose --profile gpu up -d

# Remarque : Souvent mappé sur CPU dans Docker, nécessite une configuration native sinon
docker compose --profile mps up -d
```

## Error Handling

Custom exception hierarchy with precise context:

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

### Error Raising Guidelines

**Always provide precise, actionable error messages:**

```python
# Bad: vague message
raise EmbeddingError("Embedding failed")

# Good: precise context with debugging info
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

**Error propagation chain:**

```python
try:
    vectors = await self.embedder.embed_batch(chunks)
except httpx.TimeoutException as e:
    raise EmbeddingError(
        f"Llama.cpp timeout after {self.config.timeout}s for batch of {len(chunks)} texts",
        context={"chunks_sample": chunks[:2], "timeout": self.config.timeout}
    ) from e  # Preserve original traceback
```

**HTTP error responses must include:**

```python
{
    "error": {
        "type": "embedding_error",
        "message": "Failed to embed query: connection refused",
        "details": {
            "service": "llama.cpp",
            "endpoint": "/v1/embeddings",
            "suggestion": "Verify llama.cpp server is running on configured host"
        }
    }
}
```

## Streaming Support

The `/api/v1/chat/completions` endpoint **must support both streaming and blocking modes**.

### Request Format

```json
{
  "model": "petit-prince-rag",
  "messages": [{ "role": "user", "content": "Qui est le renard?" }],
  "stream": true
}
```

### Blocking Response (stream: false)

Standard OpenAI format (see above).

### Streaming Response (stream: true)

Server-Sent Events (SSE) format:

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"petit-prince-rag","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"petit-prince-rag","choices":[{"index":0,"delta":{"content":"Le"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"petit-prince-rag","choices":[{"index":0,"delta":{"content":" renard"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"petit-prince-rag","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### Implementation Pattern

```python
async def chat_completion(request: ChatRequest) -> Response:
    # 1. Embed query (blocking - fast)
    query_vector = await embedder.embed_query(request.messages[-1].content)

    # 2. Retrieve & rerank (blocking - fast)
    documents = await retriever.search_and_rerank(query_vector)

    # 3. Build prompt
    prompt = prompt_builder.build(request.messages, documents)

    # 4. Generate (streaming or blocking based on request.stream)
    if request.stream:
        return StreamingResponse(
            generate_stream(prompt),
            media_type="text/event-stream"
        )
    else:
        response = await generator.generate(prompt)
        return JSONResponse(format_completion(response))
```

## Metrics Calculation

**Metrics must strictly follow the OpenAI API standard format.**

### OpenAI-Compliant Usage Object

The `usage` object is **mandatory** in all responses (blocking and streaming).

```json
{
  "usage": {
    "prompt_tokens": 1847,
    "completion_tokens": 234,
    "total_tokens": 2081
  }
}
```

**No additional fields in `usage`** - this object must contain exactly these three fields to remain OpenAI-compatible. Extended metrics go elsewhere.

### Blocking Response Format

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1702488550,
  "model": "petit-prince-rag",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Le renard est un personnage central..."
      },
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

### Streaming Response Format

Each chunk follows OpenAI's `chat.completion.chunk` format:

```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1702488550,"model":"petit-prince-rag","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1702488550,"model":"petit-prince-rag","choices":[{"index":0,"delta":{"content":"Le"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1702488550,"model":"petit-prince-rag","choices":[{"index":0,"delta":{"content":" renard"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1702488550,"model":"petit-prince-rag","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":1847,"completion_tokens":234,"total_tokens":2081}}

data: [DONE]
```

**Important**: `usage` appears **only in the final chunk** (where `finish_reason` is set), not in intermediate chunks.

### Token Counting Strategy

```python
# Use llama.cpp /tokenize endpoint for accurate counts
# NEVER estimate - always count precisely

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
        # Account for message formatting overhead
        total = 0
        for msg in messages:
            total += await self.count(msg["content"])
            total += 4  # Role tokens + separators (model-dependent)
        total += 2  # BOS/EOS tokens
        return total
```

### Extended Metrics (Non-OpenAI, Optional)

For debugging and monitoring, extended metrics are available via custom header `X-Include-Metrics: true`. These are returned in a **separate top-level field**, never inside `usage`:

```json
{
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "created": 1702488550,
    "model": "petit-prince-rag",
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

### Implementation Pattern

```python
@dataclass
class RequestMetrics:
    start_time: float = field(default_factory=time.perf_counter)
    embedding_ms: float = 0
    search_ms: float = 0
    rerank_ms: float = 0
    generation_ms: float = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_ms(self) -> float:
        return (time.perf_counter() - self.start_time) * 1000

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def to_openai_usage(self) -> dict:
        """Return strictly OpenAI-compliant usage object."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }
```

## Robustness: Edge Cases to Handle

**The code must gracefully handle all failure scenarios with proper error recovery, logging, and user feedback.**

### Ingestion Failures

| Scenario                                                       | Expected Behavior                                                                                               |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **Source file empty**                                          | Raise `IngestionError("Source file is empty: {path}")`, HTTP 422                                                |
| **Source file not UTF-8**                                      | Attempt decode with fallback encodings (latin-1), log warning, or raise `IngestionError` with detected encoding |
| **Source file only contains noise** (chapter headers, numbers) | Raise `IngestionError("No valid sentences extracted from source file")`                                         |
| **Qdrant unreachable at init**                                 | Retry 3x with exponential backoff, then raise `IngestionError` with connection details                          |
| **Collection deletion fails**                                  | Log warning, attempt to recreate anyway, raise if still fails                                                   |
| **Embedding batch fails mid-processing**                       | Log failed batch index, store successful embeddings, retry failed batch 2x, raise with partial progress info    |
| **Embedding dimension mismatch**                               | Raise `EmbeddingError(f"Expected dim {expected}, got {actual}")` before Qdrant insert                           |
| **Qdrant insert fails mid-batch**                              | Implement idempotent upserts with UUIDs, retry batch, log failed point IDs                                      |
| **Disk full during Qdrant write**                              | Catch Qdrant exception, raise `IngestionError` with disk space suggestion                                       |

### Retrieval Failures

| Scenario                                                | Expected Behavior                                                                              |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Query embedding returns wrong dimension**             | Raise `EmbeddingError` with expected vs actual dimensions                                      |
| **Query embedding returns empty vector**                | Raise `EmbeddingError("Empty embedding returned for query")`                                   |
| **Query embedding returns NaN/Inf values**              | Validate vector, raise `EmbeddingError("Invalid embedding values: contains NaN/Inf")`          |
| **Qdrant search timeout**                               | Retry 2x with shorter top_k, then return empty results with warning in response                |
| **Qdrant returns 0 results**                            | Continue to generation with "no context" prompt variant                                        |
| **Reranker service unavailable**                        | Fallback to vector similarity ranking, log warning, add `"reranker_fallback": true` to metrics |
| **Reranker returns invalid scores** (negative, >1, NaN) | Validate scores, fallback to vector ranking if invalid                                         |
| **Reranker timeout**                                    | Use vector search results directly, log warning                                                |

### Generation Failures

| Scenario                                                       | Expected Behavior                                                                                             |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **LLM service unavailable**                                    | Retry 2x, then HTTP 503 with `"retry_after": 30` header                                                       |
| **LLM timeout during blocking request**                        | HTTP 504 with partial context if available                                                                    |
| **Streaming connection drops mid-response**                    | Client receives incomplete stream; server logs warning with last chunk index                                  |
| **Streaming client disconnects early**                         | Server detects disconnect, stops generation, logs `"client_disconnected"`                                     |
| **LLM returns empty response**                                 | Retry once with slightly modified prompt, then return with warning                                            |
| **LLM returns malformed JSON** (in function calling scenarios) | Parse error with raw response in logs, return graceful error                                                  |
| **Token limit exceeded**                                       | Truncate context intelligently (keep most relevant docs), log warning with original vs truncated token counts |
| **Model swap fails on llama.cpp**                              | Raise `GenerationError` with model name and server response                                                   |

### Network & Infrastructure Failures

| Scenario                                 | Expected Behavior                                               |
| ---------------------------------------- | --------------------------------------------------------------- |
| **DNS resolution failure**               | Raise with hostname and suggestion to check network config      |
| **SSL certificate error**                | Raise with cert details, suggestion to verify `base_url` scheme |
| **Connection reset mid-request**         | Retry with fresh connection, log connection pool state          |
| **HTTP 429 (rate limit) from llama.cpp** | Respect `Retry-After` header, implement backoff, queue requests |
| **HTTP 5xx from llama.cpp**              | Retry 2x with exponential backoff (1s, 3s), then fail           |
| **Request payload too large**            | Split batch, retry with smaller chunks                          |

### Data Validation Failures

| Scenario                                   | Expected Behavior                                                        |
| ------------------------------------------ | ------------------------------------------------------------------------ |
| **Chat request with empty messages array** | HTTP 422 with clear validation error                                     |
| **Chat request with invalid role**         | HTTP 422 listing valid roles                                             |
| **Message content exceeds max length**     | HTTP 422 with max length and current length                              |
| **Invalid `stream` parameter type**        | HTTP 422 with type error details                                         |
| **Conversation history too long**          | Truncate oldest messages (keep system + last N), add warning to response |

### Recovery Patterns

```python
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    retryable_exceptions: tuple = (httpx.TimeoutException, httpx.NetworkError)
    retryable_status_codes: tuple = (429, 500, 502, 503, 504)

async def with_retry(
    func: Callable,
    config: RetryConfig,
    context: str
) -> Any:
    """Execute function with retry logic and detailed logging."""
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

# Partial batch recovery
async def embed_with_recovery(
    texts: list[str],
    batch_size: int
) -> list[list[float]]:
    """Embed texts with partial failure recovery."""
    results = [None] * len(texts)
    failed_indices = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            embeddings = await embed_batch(batch)
            for j, emb in enumerate(embeddings):
                results[i + j] = emb
        except EmbeddingError as e:
            logger.error("Batch %d-%d failed: %s", i, i + len(batch), e)
            failed_indices.extend(range(i, i + len(batch)))

    # Retry failed individually
    for idx in failed_indices:
        try:
            results[idx] = (await embed_batch([texts[idx]]))[0]
        except EmbeddingError:
            logger.error("Individual retry failed for index %d", idx)
            raise IngestionError(
                f"Embedding failed for {len(failed_indices)} texts after retry",
                context={"failed_indices": failed_indices[:10]}  # First 10
            )

    return results
```

## HealthChecks

### Initial lifespan start of the API

The application must not accept traffic until the underlying infrastructure is ready.

Startup Ping Sequence

At the start of the FastAPI application (lifespan), a blocking check is performed:

### Healthcheck of the Docker containers

For each of the Docker containers, create Healthchecks that are integrated with the dependencies of the other containers.

```yml
services:
  qdrant:
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:6333/healthz || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
  llama-embed:
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
      interval: 10s
      timeout: 10s
      retries: 6
      start_period: 30s
  llama-rerank:
    healthcheck:
     test: ["CMD-SHELL", "curl -f http://localhost:8081/health || exit 1"]
      interval: 10s
      timeout: 10s
      retries: 6
      start_period: 30s
  llama-gen:
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8082/health || exit 1"]
      interval: 10s
      timeout: 10s
      retries: 10
      start_period: 60s
  api:
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval: 10s
      timeout: 10s
      retries: 10
      start_period: 60s
    depends_on:
      - qdrant:
        condition: service_healthy
      - llama-embed:
        condition: service_healthy
      - llama-rerank:
        condition: service_healthy
      - llama-gen:
        condition: service_healthy
  interface:
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:80/ || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
    depends_on:
      - api:
        condition: service_healthy

```

## Testing

### Test Philosophy

**Tests must cover both happy paths and failure scenarios. Each edge case from the robustness section must have a corresponding test.**

```bash
# Unit tests (fast, mocked dependencies)
pytest tests/unit -v

# Integration tests (requires services)
pytest tests/integration -v

# Edge case tests specifically
pytest tests/unit -v -m edge_case
pytest tests/integration -v -m edge_case

# Coverage with branch coverage
pytest --cov=src --cov-branch --cov-report=html --cov-fail-under=80
```

### Test Structure

```
tests/
├── unit/
│   ├── test_config/
│   │   ├── test_settings_valid.py        # Valid configs load correctly
│   │   ├── test_settings_invalid.py      # Missing fields, bad values
│   │   └── test_settings_override.py     # ENV > .env > yml priority
│   ├── test_ingestion/
│   │   ├── test_chunker_happy.py         # Normal text chunking
│   │   ├── test_chunker_edge.py          # Empty, noise-only, special chars
│   │   ├── test_reader_happy.py          # UTF-8 file reading
│   │   └── test_reader_edge.py           # Empty, missing, wrong encoding
│   ├── test_generation/
│   │   ├── test_prompt_builder.py        # All three relevance scenarios
│   │   └── test_response_handler.py      # OpenAI format compliance
│   └── test_infrastructure/
│       ├── test_llama_client_mock.py     # Mocked HTTP responses
│       └── test_qdrant_client_mock.py    # Mocked Qdrant responses
├── integration/
│   ├── test_ingestion_pipeline.py        # Full ingestion with real services
│   ├── test_chat_blocking.py             # End-to-end blocking chat
│   ├── test_chat_streaming.py            # End-to-end streaming chat
│   └── test_failure_recovery.py          # Service failures, retries
├── fixtures/
│   ├── sample_book.txt                   # Small valid test file
│   ├── empty_file.txt                    # Empty file
│   ├── noise_only.txt                    # Only chapter headers
│   ├── latin1_encoded.txt                # Non-UTF-8 file
│   └── config_samples/
│       ├── valid_config.yml
│       ├── missing_fields.yml
│       └── invalid_values.yml
└── conftest.py                           # Shared fixtures, markers
```

### Unit Test Cases: Configuration

```python
# tests/unit/test_config/test_settings_invalid.py

class TestConfigValidation:
    """Test configuration validation catches all error cases."""

    @pytest.mark.edge_case
    def test_missing_required_field(self, tmp_path):
        """Config without llama.base_url raises ConfigurationError."""
        config_content = "llama:\n  embedding_model: Qwen"
        # ... assert raises with specific field mentioned

    @pytest.mark.edge_case
    def test_embedding_dim_zero(self):
        """embedding_dim=0 raises validation error."""

    @pytest.mark.edge_case
    def test_embedding_dim_negative(self):
        """embedding_dim=-1 raises validation error."""

    @pytest.mark.edge_case
    def test_top_x_greater_than_top_k(self):
        """top_x > top_k raises logical validation error."""

    @pytest.mark.edge_case
    def test_invalid_distance_metric(self):
        """distance='Invalid' raises validation error with valid options."""

    @pytest.mark.edge_case
    def test_source_file_not_exists(self, tmp_path):
        """Non-existent source_file raises with path in message."""

    @pytest.mark.edge_case
    def test_invalid_url_format(self):
        """Malformed base_url raises with format hint."""

    @pytest.mark.edge_case
    def test_port_out_of_range(self):
        """port=70000 raises with valid range."""

    def test_env_overrides_yml(self, monkeypatch, tmp_path):
        """Environment variables take precedence over yml."""

    def test_dotenv_overrides_yml(self, tmp_path):
        """.env file takes precedence over yml."""
```

### Unit Test Cases: Ingestion

```python
# tests/unit/test_ingestion/test_chunker_edge.py

class TestSentenceChunkerEdgeCases:
    """Test chunker handles problematic inputs."""

    @pytest.mark.edge_case
    def test_empty_text(self, chunker):
        """Empty string returns empty list, no exception."""
        assert chunker.chunk("") == []

    @pytest.mark.edge_case
    def test_whitespace_only(self, chunker):
        """Whitespace-only text returns empty list."""
        assert chunker.chunk("   \n\t\n   ") == []

    @pytest.mark.edge_case
    def test_chapter_headers_filtered(self, chunker):
        """Chapter headers are not returned as sentences."""
        text = "Chapitre I\n\nLe petit prince habitait une planète."
        result = chunker.chunk(text)
        assert "Chapitre I" not in result
        assert any("petit prince" in s for s in result)

    @pytest.mark.edge_case
    def test_roman_numerals_filtered(self, chunker):
        """Standalone roman numerals are filtered."""
        text = "IV\n\nCette planète était habitée par un roi."
        result = chunker.chunk(text)
        assert "IV" not in result

    @pytest.mark.edge_case
    def test_paragraph_numbers_filtered(self, chunker):
        """Paragraph numbers like '1.' are filtered."""

    @pytest.mark.edge_case
    def test_ellipsis_handling(self, chunker):
        """Ellipsis doesn't create false sentence boundaries."""
        text = "Il dit... puis il se tut."
        result = chunker.chunk(text)
        assert len(result) == 1  # Single sentence

    @pytest.mark.edge_case
    def test_quoted_dialogue(self, chunker):
        """Quoted dialogue is handled correctly."""
        text = '"Dessine-moi un mouton!" dit le petit prince.'
        result = chunker.chunk(text)
        assert len(result) == 1

    @pytest.mark.edge_case
    def test_very_long_sentence(self, chunker):
        """Sentences over 1000 chars are handled (logged, not truncated)."""
```

### Unit Test Cases: Embedding

```python
# tests/unit/test_infrastructure/test_llama_client_mock.py

class TestLlamaClientEmbedding:
    """Test embedding client with mocked responses."""

    def test_embed_batch_success(self, mock_httpx):
        """Successful batch returns correct vectors."""

    @pytest.mark.edge_case
    def test_embed_batch_partial_failure(self, mock_httpx):
        """Batch fails mid-way, error includes batch index."""
        mock_httpx.post.side_effect = [
            MockResponse(vectors[:16]),  # First batch OK
            httpx.TimeoutException("timeout"),  # Second batch fails
        ]
        with pytest.raises(EmbeddingError) as exc:
            await client.embed_batch(texts_32)
        assert "batch" in str(exc.value).lower()
        assert exc.value.context["successful_count"] == 16

    @pytest.mark.edge_case
    def test_embed_dimension_mismatch(self, mock_httpx):
        """Wrong embedding dimension raises with expected vs actual."""
        mock_httpx.post.return_value = MockResponse(dim=768)  # Expected 1024
        with pytest.raises(EmbeddingError) as exc:
            await client.embed_batch(["test"])
        assert "768" in str(exc.value)
        assert "1024" in str(exc.value)

    @pytest.mark.edge_case
    def test_embed_returns_nan(self, mock_httpx):
        """NaN in embedding vector raises validation error."""
        mock_httpx.post.return_value = MockResponse(vectors=[[float("nan")] * 1024])
        with pytest.raises(EmbeddingError, match="NaN"):
            await client.embed_batch(["test"])

    @pytest.mark.edge_case
    def test_embed_empty_response(self, mock_httpx):
        """Empty embedding list raises clear error."""

    @pytest.mark.edge_case
    def test_embed_timeout_with_retry(self, mock_httpx):
        """Timeout triggers retry, succeeds on 2nd attempt."""
        mock_httpx.post.side_effect = [
            httpx.TimeoutException("timeout"),
            MockResponse(vectors=valid_vectors),
        ]
        result = await client.embed_batch(["test"])
        assert result == valid_vectors
        assert mock_httpx.post.call_count == 2

    @pytest.mark.edge_case
    def test_embed_all_retries_exhausted(self, mock_httpx):
        """All retries fail, raises with attempt count."""
        mock_httpx.post.side_effect = httpx.TimeoutException("timeout")
        with pytest.raises(EmbeddingError) as exc:
            await client.embed_batch(["test"])
        assert "3" in str(exc.value)  # 3 attempts
```

### Unit Test Cases: Generation

```python
# tests/unit/test_generation/test_prompt_builder.py

class TestPromptBuilder:
    """Test prompt construction for all relevance scenarios."""

    def test_all_documents_relevant_system_prompt(self, builder):
        """All docs above threshold use 'hautement pertinents' system prompt."""
        docs = [Doc(text="...", score=0.9), Doc(text="...", score=0.85)]
        messages = builder.build(conversation, docs, threshold=0.7)
        system = messages[0]["content"]
        assert "tous hautement pertinents" in system or "hautement pertinents" in system.lower()
        assert "PERTINENCE: HAUTE" not in system  # Tags are in user msg, not system

    def test_partial_relevance_system_prompt(self, builder):
        """Mixed scores use 'pertinence variables' system prompt."""
        docs = [Doc(text="...", score=0.9), Doc(text="...", score=0.5)]
        messages = builder.build(conversation, docs, threshold=0.7)
        system = messages[0]["content"]
        assert "pertinence variable" in system.lower() or "HAUTE" in system

    def test_no_relevant_documents_system_prompt(self, builder):
        """All docs below threshold use 'pertinence limitée' system prompt."""
        docs = [Doc(text="...", score=0.3), Doc(text="...", score=0.2)]
        messages = builder.build(conversation, docs, threshold=0.7)
        system = messages[0]["content"]
        assert "pertinence limitée" in system.lower()
        assert "connaissance générale" in system.lower()

    def test_all_documents_always_in_context(self, builder):
        """ALL documents appear in context regardless of score."""
        docs = [
            Doc(text="High relevance text", score=0.9),
            Doc(text="Low relevance text", score=0.3),
        ]
        messages = builder.build(conversation, docs, threshold=0.7)
        last_user_msg = messages[-1]["content"]
        assert "High relevance text" in last_user_msg
        assert "Low relevance text" in last_user_msg  # Low score doc MUST be present

    def test_relevance_tags_in_context(self, builder):
        """Documents are tagged [HAUTE] or [MODÉRÉE] based on threshold."""
        docs = [
            Doc(text="Above threshold", score=0.8),
            Doc(text="Below threshold", score=0.5),
        ]
        messages = builder.build(conversation, docs, threshold=0.7)
        last_user_msg = messages[-1]["content"]
        assert "[PERTINENCE: HAUTE]" in last_user_msg
        assert "[PERTINENCE: MODÉRÉE]" in last_user_msg

    def test_conversation_history_preserved(self, builder):
        """Full conversation history appears before augmented user message."""
        conversation = [
            Message(role="user", content="Bonjour"),
            Message(role="assistant", content="Bonjour !"),
            Message(role="user", content="Qui est le renard?"),
        ]
        docs = [Doc(text="Le renard...", score=0.9)]
        messages = builder.build(conversation, docs, threshold=0.7)

        assert messages[1]["content"] == "Bonjour"
        assert messages[2]["content"] == "Bonjour !"
        assert "Qui est le renard?" in messages[3]["content"]
        assert "EXTRAITS DU PETIT PRINCE" in messages[3]["content"]

    def test_original_query_before_context(self, builder):
        """Original query appears before the context block."""
        conversation = [Message(role="user", content="Ma question originale")]
        docs = [Doc(text="Extrait", score=0.9)]
        messages = builder.build(conversation, docs, threshold=0.7)
        last_msg = messages[-1]["content"]

        query_pos = last_msg.index("Ma question originale")
        context_pos = last_msg.index("EXTRAITS DU PETIT PRINCE")
        assert query_pos < context_pos

    @pytest.mark.edge_case
    def test_empty_documents_list(self, builder):
        """Empty doc list uses no-context prompt variant."""
        messages = builder.build(conversation, [], threshold=0.7)
        system = messages[0]["content"]
        assert "pertinence limitée" in system.lower() or "pas d'extrait" in system.lower()

    @pytest.mark.edge_case
    def test_context_token_truncation_preserves_high_relevance(self, builder):
        """When truncating for token limit, high relevance docs are kept first."""
        docs = [
            Doc(text="A" * 5000, score=0.95),  # High, keep
            Doc(text="B" * 5000, score=0.90),  # High, keep
            Doc(text="C" * 5000, score=0.50),  # Low, truncate first
        ]
        messages = builder.build(conversation, docs, threshold=0.7, max_context_tokens=1000)
        last_msg = messages[-1]["content"]
        assert "AAAA" in last_msg  # High relevance kept
        # Low relevance may be truncated or summarized

    def test_system_prompt_contains_required_sections(self, builder):
        """System prompt includes RÔLE, SOURCES, CONTRAINTES, TON sections."""
        docs = [Doc(text="...", score=0.9)]
        messages = builder.build(conversation, docs, threshold=0.7)
        system = messages[0]["content"]

        assert "RÔLE" in system or "rôle" in system.lower()
        assert "CONTRAINTES" in system or "contraintes" in system.lower()
        assert "TON" in system.lower() or "STYLE" in system
```

### Integration Test Cases

```python
# tests/integration/test_failure_recovery.py

@pytest.mark.integration
class TestFailureRecovery:
    """Test system behavior under failure conditions."""

    @pytest.mark.edge_case
    async def test_llama_unavailable_at_chat(self, client, qdrant_running):
        """Chat request when llama.cpp is down returns 503."""
        # Stop llama.cpp container
        response = await client.post("/api/v1/chat/completions", json=valid_request)
        assert response.status_code == 503
        assert "llama" in response.json()["error"]["message"].lower()

    @pytest.mark.edge_case
    async def test_qdrant_unavailable_at_search(self, client, llama_running):
        """Search with Qdrant down returns 503 with service name."""

    @pytest.mark.edge_case
    async def test_streaming_client_disconnect(self, client, all_services):
        """Server handles client disconnect gracefully."""
        async with client.stream("POST", "/api/v1/chat/completions",
                                  json={**valid_request, "stream": True}) as response:
            await response.aiter_lines().__anext__()  # Read first chunk
            # Disconnect by exiting context
        # Assert server logged disconnect, no crash

    @pytest.mark.edge_case
    async def test_init_with_empty_file(self, client, empty_book_file):
        """Init with empty source file returns 422."""
        response = await client.post("/api/init")
        assert response.status_code == 422
        assert "empty" in response.json()["error"]["message"].lower()

    @pytest.mark.edge_case
    async def test_init_with_corrupted_qdrant(self, client, corrupted_qdrant):
        """Init handles Qdrant corruption by recreating collection."""
        response = await client.post("/api/init")
        assert response.status_code == 200  # Recovery successful

    @pytest.mark.edge_case
    async def test_chat_with_uninitialized_collection(self, client, empty_qdrant):
        """Chat before init returns helpful error."""
        response = await client.post("/api/v1/chat/completions", json=valid_request)
        assert response.status_code == 400
        assert "init" in response.json()["error"]["suggestion"].lower()

# tests/integration/test_chat_streaming.py

@pytest.mark.integration
class TestStreamingChat:
    """Test streaming chat functionality."""

    async def test_streaming_complete_response(self, client, indexed_collection):
        """Streaming returns all chunks ending with [DONE]."""
        chunks = []
        async with client.stream("POST", "/api/v1/chat/completions",
                                  json={**valid_request, "stream": True}) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunks.append(line[6:])

        assert chunks[-1] == "[DONE]"
        assert any('"finish_reason":"stop"' in c for c in chunks)

    async def test_streaming_includes_usage_in_final_chunk(self, client, indexed_collection):
        """Final chunk before [DONE] includes usage metrics."""
        # ... collect chunks
        final_data = json.loads(chunks[-2])  # Last data chunk before [DONE]
        assert "usage" in final_data
        assert final_data["usage"]["total_tokens"] > 0

    @pytest.mark.edge_case
    async def test_streaming_with_reranker_fallback(self, client, indexed_collection,
                                                      reranker_unavailable):
        """Streaming works with reranker fallback, includes warning."""
```

### Test Fixtures

```python
# tests/conftest.py

import pytest

pytest_plugins = ["pytest_asyncio"]

@pytest.fixture
def valid_config(tmp_path) -> Path:
    """Create a valid config.yml for testing."""
    config = tmp_path / "config.yml"
    config.write_text(VALID_CONFIG_YAML)
    return config

@pytest.fixture
def empty_book_file(tmp_path) -> Path:
    """Create an empty book.txt."""
    f = tmp_path / "book.txt"
    f.write_text("")
    return f

@pytest.fixture
def noise_only_book(tmp_path) -> Path:
    """Book with only chapter headers, no real content."""
    f = tmp_path / "book.txt"
    f.write_text("Chapitre I\n\nII\n\nChapitre III\n\n4.\n")
    return f

@pytest.fixture
def mock_llama_success(httpx_mock):
    """Mock llama.cpp with successful responses."""
    httpx_mock.add_response(
        url=re.compile(r".*/v1/embeddings"),
        json={"data": [{"embedding": [0.1] * 1024}]}
    )
    # ... more mocks

@pytest.fixture
def mock_llama_timeout(httpx_mock):
    """Mock llama.cpp that always times out."""
    httpx_mock.add_exception(httpx.TimeoutException("Mocked timeout"))

# Markers
def pytest_configure(config):
    config.addinivalue_line("markers", "edge_case: marks test as edge case scenario")
    config.addinivalue_line("markers", "integration: marks test as integration test")
```

### Coverage Requirements

```ini
# pyproject.toml or setup.cfg

[tool.coverage.run]
branch = true
source = ["src"]
omit = ["src/__main__.py"]

[tool.coverage.report]
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]
```

---

## Test Suite Status & Roadmap

### Current Implementation Status (December 2024)

#### ✅ **Completed Tests**

**Unit Tests - Configuration** (10 tests)
- ✅ Valid YAML loading ([test_settings_valid.py](tests/unit/test_config/test_settings_valid.py))
- ✅ ENV variable override priority
- ✅ Default values application
- ✅ Invalid configuration detection (missing fields, bad values, constraints)
- ✅ Port/URL/collection name validation

**Unit Tests - Ingestion** (12 tests)
- ✅ Sentence chunking ([test_chunker.py](tests/unit/test_ingestion/test_chunker.py))
- ✅ Paragraph building ([test_paragraph_builder.py](tests/unit/test_ingestion/test_paragraph_builder.py))
- ✅ Text reader ([test_reader.py](tests/unit/test_ingestion/test_reader.py))
- ✅ Edge cases: empty text, whitespace, chapter headers, roman numerals
- ✅ French text specifics: ellipsis, quoted dialogue

**Unit Tests - Generation** (12 tests)
- ✅ Prompt building for 3 relevance scenarios ([test_prompt_builder.py](tests/unit/test_generation/test_prompt_builder.py))
- ✅ Context injection format
- ✅ Conversation history preservation
- ✅ OpenAI response format compliance ([test_response_handler.py](tests/unit/test_generation/test_response_handler.py))
- ✅ Streaming SSE format
- ✅ Extended metrics (x_metrics) handling

**Test Infrastructure**
- ✅ Pytest markers configured (edge_case, integration)
- ✅ Basic fixtures (config samples, empty files, sample book)
- ✅ Test file organization (unit/integration separation)

**Total Implemented: 34 unit tests**

---

#### ❌ **Critical Missing Tests (BLOCKERS FOR PRODUCTION)**

##### 🔴 **1. Infrastructure Layer Tests (0/25 tests implemented)**

**PRIORITY: URGENT** - Ces composants gèrent 80% des erreurs en production

**Missing: `tests/unit/test_infrastructure/test_llama_client.py`**
```python
# Embedding tests (0/10 implemented)
❌ test_embed_batch_success()
❌ test_embed_batch_partial_failure_with_recovery()
❌ test_embed_dimension_mismatch()
❌ test_embed_returns_nan_or_inf()
❌ test_embed_empty_response()
❌ test_embed_timeout_with_retry()
❌ test_embed_all_retries_exhausted()
❌ test_embed_http_500_with_retry()
❌ test_embed_http_429_rate_limit()
❌ test_embed_malformed_json_response()

# Reranking tests (0/8 implemented)
❌ test_rerank_success()
❌ test_rerank_unavailable_fallback_to_vector_search()
❌ test_rerank_timeout()
❌ test_rerank_invalid_scores()
❌ test_rerank_empty_documents()
❌ test_rerank_returns_fewer_than_requested()
❌ test_rerank_service_returns_error()
❌ test_rerank_malformed_response()

# Generation tests (0/7 implemented)
❌ test_generate_blocking_success()
❌ test_generate_streaming_success()
❌ test_generate_timeout()
❌ test_generate_empty_response()
❌ test_generate_token_limit_exceeded()
❌ test_generate_model_swap_failure()
❌ test_generate_streaming_client_disconnect()
```

**Missing: `tests/unit/test_infrastructure/test_qdrant_client.py`**
```python
# Vector operations (0/12 implemented)
❌ test_create_collection_success()
❌ test_create_collection_already_exists()
❌ test_upsert_vectors_success()
❌ test_upsert_dimension_mismatch()
❌ test_upsert_batch_partial_failure()
❌ test_search_vectors_success()
❌ test_search_empty_results()
❌ test_search_timeout()
❌ test_search_collection_not_found()
❌ test_delete_collection_success()
❌ test_qdrant_connection_refused()
❌ test_qdrant_disk_full()
```

##### 🔴 **2. Integration Tests (0/15 tests implemented)**

**PRIORITY: URGENT** - Aucun test end-to-end actuellement

**All integration tests are currently SKIPPED** ([test_api.py](tests/integration/test_api.py))

**Missing: `tests/integration/test_ingestion_pipeline.py`**
```python
❌ test_full_ingestion_pipeline_success()
❌ test_ingestion_with_real_book_file()
❌ test_ingestion_duplicate_handling()
❌ test_ingestion_progress_reporting()
```

**Missing: `tests/integration/test_chat_blocking.py`**
```python
❌ test_chat_blocking_with_indexed_collection()
❌ test_chat_blocking_with_metrics()
❌ test_chat_blocking_openai_format_compliance()
```

**Missing: `tests/integration/test_chat_streaming.py`**
```python
❌ test_chat_streaming_complete_response()
❌ test_chat_streaming_includes_usage_in_final_chunk()
❌ test_chat_streaming_client_disconnect()
❌ test_chat_streaming_with_reranker_fallback()
```

**Missing: `tests/integration/test_failure_recovery.py`**
```python
❌ test_llama_unavailable_at_chat()
❌ test_qdrant_unavailable_at_search()
❌ test_init_with_empty_file()
❌ test_chat_with_uninitialized_collection()
```

##### 🔴 **3. Critical Edge Cases (0/25 implemented)**

**Ingestion Edge Cases**
```python
❌ test_read_latin1_encoded_file()  # Non-UTF-8 encoding
❌ test_read_very_large_file()      # >100MB file
❌ test_chunk_very_long_sentence()  # >1000 chars
❌ test_chunk_malformed_french()    # Corrupted UTF-8
❌ test_embed_batch_mid_failure_recovery()  # Partial batch failure
```

**Retrieval Edge Cases**
```python
❌ test_query_embedding_returns_nan()
❌ test_query_embedding_returns_inf()
❌ test_vector_dimension_mismatch()
❌ test_qdrant_search_timeout()
❌ test_reranker_unavailable_fallback()
❌ test_no_documents_above_threshold()
```

**Generation Edge Cases**
```python
❌ test_llm_timeout_during_streaming()
❌ test_llm_returns_empty_response()
❌ test_token_limit_exceeded_with_truncation()
❌ test_streaming_connection_drops()
❌ test_malformed_llm_response()
❌ test_context_too_large_for_model()
```

**API Edge Cases**
```python
❌ test_empty_messages_array()
❌ test_invalid_role_in_message()
❌ test_message_content_exceeds_limit()
❌ test_conversation_history_too_long()
❌ test_concurrent_requests()
❌ test_rate_limiting()
❌ test_request_timeout()
```

---

#### 🟡 **Moderate Priority Missing Tests**

##### **4. Test Fixtures & Utilities (0/10 implemented)**

**Missing: Reusable fixtures in `conftest.py`**
```python
❌ @pytest.fixture def mock_httpx_client()
❌ @pytest.fixture def mock_llama_responses()
❌ @pytest.fixture def mock_qdrant_client()
❌ @pytest.fixture def valid_embeddings()
❌ @pytest.fixture def sample_ranked_documents()
❌ @pytest.fixture def indexed_test_collection()
❌ @pytest.fixture def llama_server_running()
❌ @pytest.fixture def qdrant_server_running()
❌ @pytest.fixture def complete_test_environment()
❌ @pytest.fixture def performance_metrics_tracker()
```

##### **5. Assertion Strengthening (12 tests need improvement)**

Current weak assertions in existing tests:
```python
# test_prompt_builder.py:24 - Too permissive
❌ assert "hautement pertinent" in system.lower() or "tous" in system.lower()
   Should be: assert "tous hautement pertinents" in system.lower()

# test_prompt_builder.py:38 - Too vague
❌ assert "variable" in system.lower() or "haute" in system
   Should verify complete structure

# test_response_handler.py:68 - Missing type validation
❌ assert set(usage.keys()) == {"prompt_tokens", "completion_tokens", "total_tokens"}
   Should also assert isinstance(usage["prompt_tokens"], int)
   Should also assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
```

**Tasks:**
- [ ] Strengthen 12 existing assertions with precise format validation
- [ ] Add type checking for all numeric fields
- [ ] Verify consistency constraints (e.g., total = prompt + completion)
- [ ] Add negative value detection

##### **6. Coverage Configuration (Not configured)**

**Missing: `pyproject.toml` coverage section**
```toml
❌ [tool.coverage.run]
❌ [tool.coverage.report] fail_under = 80
❌ [tool.coverage.html]
```

**Missing: Coverage enforcement in CI/CD**
```yaml
❌ pytest --cov=src --cov-branch --cov-fail-under=80
```

---

#### 🟢 **Low Priority Enhancements**

##### **7. Performance Tests (0/8 implemented)**

```python
❌ @pytest.mark.performance
   def test_embedding_batch_speed_under_1s_for_100_texts()

❌ def test_ingestion_memory_usage_under_500mb()

❌ def test_chat_response_time_under_5s()

❌ def test_streaming_first_token_latency_under_500ms()

❌ def test_qdrant_search_under_50ms()

❌ def test_concurrent_requests_throughput()

❌ def test_reranking_speed_proportional_to_doc_count()

❌ def test_token_counting_accuracy()
```

##### **8. Security Tests (0/6 implemented)**

```python
❌ def test_prompt_injection_prevention()
❌ def test_path_traversal_in_ingestion()
❌ def test_oversized_request_rejection()
❌ def test_sql_injection_in_metadata()
❌ def test_xss_in_chat_responses()
❌ def test_dos_protection()
```

##### **9. Property-Based Testing with Hypothesis (0/5 implemented)**

```python
❌ @given(text=st.text())
   def test_chunker_never_crashes(text)

❌ @given(sentences=st.lists(st.text()))
   def test_paragraph_builder_preserves_sentence_count(sentences)

❌ @given(vector=st.lists(st.floats(), min_size=768, max_size=768))
   def test_vector_validation_handles_all_floats(vector)

❌ @given(conversation=st.lists(st.builds(Message)))
   def test_prompt_builder_never_crashes(conversation)

❌ @given(tokens=st.integers(min_value=0, max_value=100000))
   def test_token_counting_consistency(tokens)
```

---

### Test Coverage Metrics

#### Current Status
| Category | Tests Implemented | Tests Specified | Coverage % | Target % |
|----------|------------------|-----------------|------------|----------|
| **Unit - Config** | 10 | 12 | 83% | 100% |
| **Unit - Ingestion** | 12 | 18 | 67% | 100% |
| **Unit - Generation** | 12 | 15 | 80% | 100% |
| **Unit - Infrastructure** | 0 | 37 | 0% | 90% |
| **Integration** | 0 | 15 | 0% | 80% |
| **Edge Cases** | 15 | 40 | 38% | 100% |
| **TOTAL** | **34** | **137** | **25%** | **85%** |

#### Code Coverage (Estimated)
- **Current**: ~40% line coverage, ~30% branch coverage
- **Target**: 80% line coverage, 70% branch coverage
- **Blockers**: Infrastructure layer (0%), Integration tests (0%)

---

### Implementation Roadmap

#### 🔥 **Sprint 1: Production Readiness (5 days - URGENT)**

**Goal**: Unlock production deployment with critical infrastructure tests

**Tasks:**
1. [ ] Implement `test_llama_client.py` (25 tests - 2 days)
   - All embedding tests with mocked httpx
   - Reranking tests with fallback scenarios
   - Generation tests (blocking + streaming)

2. [ ] Implement `test_qdrant_client.py` (12 tests - 1 day)
   - Collection management
   - Vector operations with error handling
   - Connection failure scenarios

3. [ ] Create reusable fixtures in `conftest.py` (1 day)
   - `mock_httpx_client`
   - `mock_llama_responses`
   - `valid_embeddings`
   - `sample_ranked_documents`

4. [ ] Setup coverage configuration (0.5 day)
   - Add `pyproject.toml` coverage section
   - Configure pytest-cov
   - Add pre-commit hook for coverage check

5. [ ] Implement 1 E2E test (0.5 day)
   - `test_init_and_chat_blocking_full_pipeline()`

**Deliverables:**
- 37 infrastructure tests passing
- 1 E2E test passing
- Coverage reporting configured
- Coverage: ~60% (from 40%)

**Acceptance Criteria:**
- All infrastructure tests green
- No mocked services in E2E test
- Coverage report generated
- Can run: `pytest tests/unit/test_infrastructure -v`

---

#### ⚡ **Sprint 2: Robustness & Integration (8 days - HIGH PRIORITY)**

**Goal**: Complete integration tests and critical edge cases

**Tasks:**
1. [ ] Implement integration tests (15 tests - 4 days)
   - Setup Docker Compose test environment
   - Full ingestion pipeline test
   - Chat blocking + streaming tests
   - Failure recovery scenarios

2. [ ] Implement critical edge cases (25 tests - 3 days)
   - Non-UTF-8 encoding handling
   - NaN/Inf vector validation
   - Streaming disconnect scenarios
   - Token limit exceeded with truncation
   - Reranker fallback behavior

3. [ ] Strengthen existing assertions (1 day)
   - Review all 34 existing tests
   - Add strict format validation
   - Add type checking
   - Verify consistency constraints

**Deliverables:**
- 15 integration tests passing
- 25 edge case tests passing
- All existing tests strengthened
- Coverage: ~75% (from 60%)

**Acceptance Criteria:**
- Can run full test suite with real services
- All edge cases from specification covered
- No weak assertions remaining
- Can run: `pytest tests/integration -v`

---

#### 📈 **Sprint 3: Excellence & Optimization (5 days - MEDIUM PRIORITY)**

**Goal**: Performance, security, and advanced testing techniques

**Tasks:**
1. [ ] Performance tests (8 tests - 2 days)
   - Embedding speed benchmarks
   - Memory usage monitoring
   - Response time validation
   - Concurrent request handling

2. [ ] Security tests (6 tests - 1.5 days)
   - Prompt injection prevention
   - Path traversal protection
   - DoS protection
   - Input sanitization

3. [ ] Property-based testing (5 tests - 1.5 days)
   - Hypothesis integration
   - Fuzz testing for chunker
   - Invariant testing for prompt builder

**Deliverables:**
- 19 additional tests (performance + security + property-based)
- Coverage: ~85% (from 75%)
- Performance baselines documented
- Security audit passed

**Acceptance Criteria:**
- Performance benchmarks in CI/CD
- No security vulnerabilities
- Property tests find no crashes
- Can run: `pytest -m performance -v`

---

### Quick Start for Future Implementation

#### **For immediate work on infrastructure tests:**

```bash
# 1. Install test dependencies
pip install pytest pytest-asyncio pytest-httpx pytest-mock pytest-cov

# 2. Create test file
touch tests/unit/test_infrastructure/test_llama_client.py

# 3. Start with this template:
"""Tests for LlamaClient with mocked HTTP responses."""

import pytest
from pytest_httpx import HTTPXMock
from src.infrastructure.llama_client import LlamaClient
from src.core.exceptions import EmbeddingError

@pytest.fixture
def llama_client(valid_config):
    return LlamaClient(valid_config.llama)

@pytest.fixture
def valid_embeddings():
    return [[0.1] * 1024 for _ in range(10)]

class TestLlamaClientEmbedding:
    @pytest.mark.asyncio
    async def test_embed_batch_success(self, llama_client, httpx_mock, valid_embeddings):
        """Successful batch embedding returns correct vectors."""
        httpx_mock.add_response(
            url="http://localhost:8080/v1/embeddings",
            json={"data": [{"embedding": emb} for emb in valid_embeddings]}
        )

        texts = [f"text_{i}" for i in range(10)]
        result = await llama_client.embed_batch(texts)

        assert len(result) == 10
        assert len(result[0]) == 1024
        assert all(isinstance(x, float) for x in result[0])

# 4. Run tests
pytest tests/unit/test_infrastructure/test_llama_client.py -v
```

#### **For integration tests:**

```bash
# 1. Setup Docker Compose test environment
docker-compose -f docker-compose.test.yml up -d

# 2. Create integration test
touch tests/integration/test_chat_blocking.py

# 3. Use this pattern:
@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_blocking_full_pipeline():
    """Full E2E test: init → index → chat → verify response."""
    # 1. Initialize collection
    # 2. Send chat request
    # 3. Verify OpenAI format
    # 4. Check metrics
    # 5. Validate response content
```

---

### Notes for Claude Code

When implementing tests:

1. **Priority Order**: Infrastructure → Integration → Edge Cases → Performance/Security
2. **Always mock external services** in unit tests (use `pytest-httpx` for HTTP mocking)
3. **Use parametrize** for testing multiple scenarios:
   ```python
   @pytest.mark.parametrize("dim,expected_error", [
       (0, "must be greater than 0"),
       (-1, "must be greater than 0"),
       (10000, "must be less than 8192"),
   ])
   def test_invalid_embedding_dim(dim, expected_error):
       ...
   ```
4. **Edge case marker** is mandatory for all edge case tests: `@pytest.mark.edge_case`
5. **Integration marker** is mandatory for all integration tests: `@pytest.mark.integration`
6. **Assertions must be specific**:
   - ❌ Bad: `assert "error" in str(exc)`
   - ✅ Good: `assert "Embedding dimension mismatch: expected 1024, got 768" in str(exc.value)`
7. **Test docstrings are mandatory** - they serve as living documentation
8. **Follow the existing test structure** in implemented tests as reference

---

## Notes for Claude Code

1. **Start with interfaces** in `core/interfaces/` before implementations
2. **Config first**: Implement settings.py with full priority chain before other modules
3. **Test chunking** on actual book.txt - French text has specific punctuation patterns
4. **Batch wisely**: llama.cpp has context limits, test optimal batch_size
5. **Log generously at DEBUG level** - RAG debugging requires visibility into scores/vectors
6. **Type hints everywhere** - Use modern Python 3.11+ syntax (`list[str]` not `List[str]`)

# Le Petit Prince — Chatbot RAG + MCP

Ce chatbot permet d'interroger l'œuvre *Le Petit Prince* d'Antoine de Saint-Exupéry via une interface conversationnelle moderne. Il repose sur une architecture **RAG** (Retrieval-Augmented Generation) couplée au protocole **MCP** (Model Context Protocol), avec un LLM configurable via API compatible OpenAI.

---

## Architecture

```
Frontend (Next.js)
    │  HTTP / SSE
    ▼
Gateway (FastAPI)          ←→  LLM endpoint (Ollama, vLLM, OpenRouter…)
    │  MCP SSE
    ▼
MCP Server (FastAPI)
    ├── tool: retriever    →  Qdrant (vecteurs SPLADE)
    └── tool: web_search   →  SearXNG (domaines autorisés)
                                │
                       Indexer ─┘  (pipeline one-shot)
                       Embeddings  (SPLADE V3)
```

Le système est découpé en modules Python indépendants (workspace `uv`) et une interface React. Chaque module a une responsabilité claire et communique via API REST ou MCP.

---

## Modules

| Module | Rôle | Port |
|--------|------|------|
| [`embeddings/`](./embeddings/) | Encodeur sparse SPLADE V3 (partagé) | — |
| [`indexer/`](./indexer/) | Pipeline d'indexation du livre dans Qdrant | — |
| [`qdrant_manager/`](./qdrant_manager/) | Client Qdrant (collection, upsert, recherche) | — |
| [`mcp_server/`](./mcp_server/) | Serveur MCP exposant les tools au LLM | 8001 |
| [`gateway/`](./gateway/) | Orchestrateur API (chat, streaming, tool loop) | 8000 |
| [`prompts/`](./prompts/) | Registre centralisé des prompts (YAML) | — |
| [`frontend/`](./frontend/) | Interface utilisateur React / Next.js | 3000 |

---

## Démarrage rapide

### Prérequis

- Docker + Docker Compose
- Un modèle accessible via une API compatible OpenAI (Ollama, vLLM, llama.cpp, OpenRouter…)
- Un token HuggingFace pour le téléchargement de SPLADE V3

### Configuration

```bash
cp .env.example .env
# Éditer .env : LLM_BASE_URL, LLM_MODEL, HF_TOKEN
```

### Lancement des services

```bash
docker compose up -d
```

### Indexation du livre

```bash
# Placer le fichier texte du livre dans data/
docker compose run --rm indexer python -m indexer --source /data/le_petit_prince.txt --reset
```

### Accès

- Interface : http://localhost:3000
- Gateway API : http://localhost:8000
- MCP Server : http://localhost:8001
- Qdrant dashboard : http://localhost:6333/dashboard

---

## Fonctionnalités

- **Chat persistant / éphémère** — historique local via IndexedDB ou session en mémoire
- **Retrieval sémantique** — recherche sparse SPLADE V3 dans les extraits du livre
- **Web search ciblée** — restreinte à `monpetitprince.fr` et `fr.wikipedia.org` via SearXNG
- **Streaming avec thinking** — les phases de réflexion du LLM et les appels outils sont streamés en temps réel
- **Citations inline** — chaque réponse est sourcée avec des références numérotées `[1]`, `[2]`…
- **Titrage automatique** — titre de conversation généré silencieusement après le premier échange

---

## Stack technique

**Backend**
- Python 3.13, uv (workspace monorepo)
- FastAPI, Pydantic v2
- `sentence-transformers` (SPLADE V3), PyTorch
- `qdrant-client`, `mcp` (Model Context Protocol)
- SearXNG (moteur de recherche auto-hébergé)

**Frontend**
- Next.js 16 (App Router), React 19, TypeScript
- Tailwind CSS v4, Zustand, `idb`

---

## Variables d'environnement

Voir [`.env.example`](./.env.example) pour la liste complète des variables avec leurs descriptions.

Les variables essentielles :

```bash
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=mistral-nemo:latest
HF_TOKEN=hf_...
QDRANT_URL=http://qdrant:6333
SEARCH_ENGINE_URL=http://searxng:8080
NEXT_PUBLIC_ORCHESTRATOR_URL=http://localhost:8000
```

---

## Structure du dépôt

```
.
├── embeddings/          # Encodeur SPLADE V3
├── indexer/             # Pipeline d'indexation
├── qdrant_manager/      # Client vector DB
├── mcp_server/          # Serveur MCP (tools)
├── gateway/             # Orchestrateur API
├── prompts/             # Prompts centralisés
├── frontend/            # Interface utilisateur
├── data/                # Sources du livre (non versionné)
├── searxng/             # Configuration SearXNG
├── compose.yml
├── Dockerfile
└── .env.example
```

---

## Auteur

Lohan — Projet Étudiant 2026

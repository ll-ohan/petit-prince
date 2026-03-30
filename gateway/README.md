# gateway — Orchestrateur API

API Gateway FastAPI qui fait l'interface entre le frontend et le LLM. Il injecte les tools MCP dans chaque requête, orchestre la boucle d'appels outils et retransmet le stream SSE au client.

---

## Rôle dans l'architecture

```
Frontend
    │  POST /chat/completions  (SSE)
    ▼
Gateway :8000
    ├──→  LLM endpoint (OpenAI-compatible)
    │      ← stream SSE (thinking, tool_calls, text)
    │
    ├──→  MCP Server :8001  (tool calls)
    │      ← tool results
    │
    └──→  Frontend  (SSE re-streamé)
           thinking / tool_call_start / tool_result / text / done
```

Le gateway est le seul point de contact du frontend. Il est **compatible OpenAI API spec**, ce qui permet de le connecter à n'importe quel client OpenAI sans modification.

---

## Endpoints

### `POST /chat/completions`

Endpoint principal, compatible OpenAI Chat Completions. Supporte le streaming SSE.

**Requête :**
```json
{
  "model": "mistral-nemo:latest",
  "messages": [
    { "role": "user", "content": "Qui est le petit prince ?" }
  ],
  "stream": true,
  "temperature": 0.7
}
```

Le système injecte automatiquement :
- Le prompt système (`prompts.yaml` → `system.expert`)
- Les définitions des tools MCP

**Comportement :**
1. Injection du system prompt et des tools dans la requête
2. Forward vers `LLM_BASE_URL/chat/completions`
3. Parsing du stream SSE : thinking, tool_calls, texte partiel, texte final
4. Si tool_call détecté : appel MCP → injection du résultat → re-forward LLM
5. Répétition jusqu'à `finish_reason: stop` ou limite d'itérations

**Événements SSE retournés :**

| Événement | Description |
|-----------|-------------|
| `thinking` | Phase de réflexion du LLM |
| `tool_call_start` | Appel outil lancé (nom + arguments) |
| `tool_result` | Résultat de l'outil (+ durée d'exécution) |
| `text` | Fragment de texte de la réponse |
| `done` | Fin du stream (`[DONE]`) |

---

### `GET /models`

Retourne la liste des modèles disponibles depuis le LLM endpoint configuré.

---

### `POST /responses`

Endpoint alternatif compatible OpenAI Responses API. Wrapping de `/chat/completions` avec adaptation du format entrée/sortie.

---

### `POST /embeddings`

Délègue au module `embeddings` pour encoder du texte en vecteur sparse SPLADE.

---

### `POST /titrate`

Génère un titre court (3–6 mots) pour une conversation. Utilisé par le frontend après le premier échange.

**Requête :**
```json
{
  "user_message": "Qui est le renard dans le livre ?",
  "assistant_summary": "Le renard est un personnage clé du chapitre XXI..."
}
```

**Réponse :**
```json
{ "title": "Le renard et l'apprivoisement" }
```

---

### `GET /health`

Vérifie l'état du gateway et la connexion au MCP Server.

---

## Boucle tool loop

Le gateway gère des séquences entrelacées : un LLM peut émettre du thinking, un tool call, du texte partiel, un nouveau thinking, un nouveau tool call, avant la réponse finale. Cette complexité est abstraite dans `services/tool_loop.py`.

```python
# Limite de sécurité
MAX_TOOL_ITERATIONS = 8  # configurable via .env
```

La détection des tool calls supporte deux formats :
- **Format natif** : `delta.tool_calls` (standard OpenAI)
- **Format inline** : `[TOOL_CALLS] nom_outil [ARGS] {...}` (certains modèles locaux)

De même pour le thinking :
- **Format natif** : champ `reasoning_content` ou `thinking` dans le delta
- **Format inline** : balises `<think>...</think>` dans le contenu

---

## Structure

```
gateway/
├── pyproject.toml
└── src/gateway/
    ├── __init__.py
    ├── main.py              # Application FastAPI, CORS, lifespan
    ├── config.py            # GatewaySettings (pydantic-settings)
    ├── routers/
    │   ├── chat.py          # POST /chat/completions
    │   ├── responses.py     # POST /responses
    │   ├── models.py        # GET /models
    │   ├── embeddings.py    # POST /embeddings
    │   └── titrate.py       # POST /titrate
    ├── schemas/
    │   ├── chat.py          # ChatRequest, ChatMessage, Delta
    │   └── titrate.py       # TitrateRequest, TitrateResponse
    └── services/
        ├── mcp_client.py    # MCPConnectionManager (connexion SSE persistante)
        └── tool_loop.py     # Boucle ping-pong LLM ↔ MCP
```

---

## Configuration

| Variable d'environnement | Valeur par défaut | Description |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:11434/v1` | URL du LLM (compatible OpenAI) |
| `LLM_MODEL` | `mistral-nemo:latest` | Modèle utilisé |
| `LLM_API_KEY` | — | Clé API (optionnelle) |
| `LLM_TEMPERATURE` | `0.7` | Température de génération |
| `LLM_MAX_TOKENS` | `4096` | Tokens maximum par réponse |
| `MAX_TOOL_ITERATIONS` | `8` | Limite de cycles tool call |
| `MCP_SERVER_URL` | `http://mcp_server:8001` | URL du serveur MCP |
| `ORCHESTRATOR_PORT` | `8000` | Port d'écoute du gateway |

---

## CORS

Le gateway est configuré pour autoriser les requêtes depuis `http://localhost:3000` en développement. En production, restreindre `allow_origins` au domaine du frontend.

---

## Dépendances

```
fastapi >= 0.135.2
prompts @ ../prompts     (workspace local)
embeddings @ ../embeddings
```

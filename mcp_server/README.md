# mcp_server — Serveur MCP

Serveur implémentant le protocole **MCP (Model Context Protocol)** en mode HTTP SSE. Il expose deux outils au LLM : `retriever` pour la recherche dans le livre, et `web_search` pour la recherche web sur les sites autorisés.

---

## Rôle dans l'architecture

```
Gateway (orchestrateur)
    │  MCP SSE  (GET /sse + POST /messages)
    ▼
MCP Server :8001
    ├── tool: retriever   →  SpladeEncoder  →  Qdrant
    └── tool: web_search  →  SearXNG  →  filtrage domaines
```

Le gateway s'y connecte comme client MCP via une connexion SSE persistante. Les appels outils sont envoyés en JSON-RPC sur `POST /messages` et les résultats reviennent via le stream SSE ouvert.

---

## Outils exposés

### `retriever`

Recherche sémantique dans les extraits du *Petit Prince* indexés dans Qdrant.

**Paramètres :**

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `query` | string | oui | Requête en langage naturel |
| `top_k` | integer | non | Nombre de résultats (1–10, défaut : 5) |
| `chapter_filter` | integer | non | Filtrer par numéro de chapitre |

**Exemple de retour :**

```json
{
  "results": [
    {
      "ref_id": 1,
      "text": "On ne voit bien qu'avec le cœur. L'essentiel est invisible pour les yeux.",
      "chapter": 21,
      "page": 72,
      "score": 0.847
    }
  ],
  "query": "apprivoiser le renard",
  "total": 5
}
```

**Logique interne :**
1. Encoder la requête avec `SpladeEncoder.encode_query()`
2. Rechercher dans Qdrant sur le vecteur `splade` avec filtre optionnel de chapitre
3. Formatter et retourner les résultats avec des `ref_id` numérotés

---

### `web_search`

Recherche sur les sites autorisés uniquement : `www.monpetitprince.fr` et `fr.wikipedia.org`.

**Paramètres :**

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `query` | string | oui | Requête de recherche |
| `site` | enum | non | `all`, `monpetitprince.fr`, `fr.wikipedia.org` (défaut : `all`) |
| `max_results` | integer | non | Nombre max de résultats (1–5, défaut : 3) |

**Exemple de retour :**

```json
{
  "results": [
    {
      "ref_id": 6,
      "title": "Le Petit Prince — Wikipédia",
      "url": "https://fr.wikipedia.org/wiki/Le_Petit_Prince",
      "snippet": "Le Petit Prince est une œuvre de langue française...",
      "source_domain": "fr.wikipedia.org"
    }
  ],
  "query": "biographie Saint-Exupéry",
  "total": 1
}
```

**Logique interne :**
1. Envoyer la requête à SearXNG avec restriction de domaine
2. Filtrer strictement les URLs retournées contre la liste blanche
3. Récupérer le contenu HTML des pages retenues (BeautifulSoup)
4. Extraire et nettoyer le texte pertinent
5. Retourner les extraits avec leur source

**Liste blanche (stricte) :**
```python
ALLOWED_DOMAINS = [
    "www.monpetitprince.fr",
    "fr.wikipedia.org"
]
# Toute URL ne correspondant pas à cette liste est rejetée silencieusement.
```

---

## Transport MCP

Le serveur utilise le transport **HTTP SSE** du SDK MCP Python :

```
GET  /sse       →  établissement de la connexion SSE (keep-alive)
POST /messages  →  envoi des appels tools (JSON-RPC 2.0)
```

Ce mode permet au gateway de maintenir une connexion persistante et de recevoir les résultats de façon asynchrone.

---

## Endpoints complémentaires

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Vérifie la connectivité Qdrant + état du serveur |

---

## Structure

```
mcp_server/
├── pyproject.toml
└── src/mcp_server/
    ├── __init__.py
    ├── main.py          # Application FastAPI + déclaration des tools MCP
    ├── config.py        # Variables d'environnement
    ├── tools/
    │   ├── __init__.py
    │   ├── retriever.py  # Logique retrieval (encode + search Qdrant)
    │   └── web_search.py # Logique web search (SearXNG + filtrage)
    └── schemas/
        ├── __init__.py
        ├── retriever.py  # RetrieverInput, RetrieverOutput
        └── web_search.py # WebSearchInput, WebSearchOutput
```

---

## Configuration

| Variable d'environnement | Valeur par défaut | Description |
|---|---|---|
| `QDRANT_URL` | `http://qdrant:6333` | URL du serveur Qdrant |
| `QDRANT_COLLECTION` | `petit_prince` | Nom de la collection |
| `SEARCH_ENGINE_URL` | `http://searxng:8080` | URL SearXNG |
| `ALLOWED_DOMAINS` | `www.monpetitprince.fr,fr.wikipedia.org` | Liste blanche (CSV) |
| `SPLADE_MODEL` | `naver/splade-v3` | Modèle d'encodage |
| `SPLADE_DEVICE` | `cpu` | Device PyTorch |

---

## Dépendances

```
fastapi >= 0.135.2
mcp >= 1.26.0
beautifulsoup4 >= 4.14.3
embeddings @ ../embeddings   (workspace local)
qdrant_manager @ ../qdrant_manager
```

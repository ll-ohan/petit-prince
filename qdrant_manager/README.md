# qdrant_manager — Client Qdrant

Module utilitaire qui centralise toutes les interactions avec la base vectorielle **Qdrant**. Il est importé aussi bien par le pipeline d'indexation que par le serveur MCP pour le retrieval.

---

## Rôle dans l'architecture

```
indexer      ──→  qdrant_manager  ──→  Qdrant :6333
mcp_server   ──→  qdrant_manager  ──┘   (collection "petit_prince")
```

Le module gère trois responsabilités distinctes :
- la connexion au serveur Qdrant (singleton)
- la création et la configuration de la collection
- l'insertion et la recherche de vecteurs

---

## Collection Qdrant

La collection `petit_prince` est configurée pour n'utiliser que des **vecteurs sparse** (pas de vecteurs dense). Ce choix est cohérent avec l'usage exclusif de SPLADE V3, qui produit uniquement des représentations sparse.

```python
# Configuration appliquée à la création
client.create_collection(
    collection_name="petit_prince",
    vectors_config={},          # pas de vecteur dense
    sparse_vectors_config={
        "splade": SparseVectorParams(
            index=SparseIndexParams(on_disk=False)
        )
    }
)
```

---

## Interface

### Initialisation de la collection

```python
from qdrant_manager.index import setup_collection

# Crée la collection si elle n'existe pas (ou la recrée si reset=True)
setup_collection(reset=True)
```

### Insertion de chunks

```python
from qdrant_manager.index import upsert_chunks
from embeddings.sparse.models import SparseVector

upsert_chunks([
    {
        "content_hash": "sha256:abc...",
        "text": "On ne voit bien qu'avec le cœur...",
        "chapter_id": 21,
        "page_start": 72,
        "page_end": 72,
        "chunk_index": 3,
        "sparse_vector": SparseVector(indices=[...], values=[...])
    }
])
```

L'ID Qdrant est dérivé du `content_hash` via UUID v5 : l'opération est donc **idempotente**.

### Recherche de passages

```python
from qdrant_manager.retrieve import search_passages
from embeddings.sparse.models import SparseVector

results = search_passages(
    query_vector=SparseVector(indices=[...], values=[...]),
    top_k=5,
    chapter_filter=21   # optionnel
)

# Résultat : list[PassageResult]
# [
#   { "ref_id": 1, "text": "...", "chapter": 21, "page": 72, "score": 0.847 },
#   ...
# ]
```

---

## Structure

```
qdrant_manager/
├── pyproject.toml
└── src/qdrant_manager/
    ├── __init__.py
    ├── client.py      # Singleton QdrantClient + configuration env
    ├── index.py       # setup_collection(), upsert_chunks()
    └── retrieve.py    # search_passages()
```

---

## Configuration

| Variable d'environnement | Valeur par défaut | Description |
|---|---|---|
| `QDRANT_URL` | `http://qdrant:6333` | URL du serveur Qdrant |
| `QDRANT_COLLECTION` | `petit_prince` | Nom de la collection |

---

## Types

```python
class PassageResult(TypedDict):
    ref_id: int          # Numéro de référence (1-indexed, pour les citations)
    text: str            # Contenu du passage
    chapter: int         # Numéro de chapitre
    page: int            # Numéro de page (page_start)
    score: float         # Score de similarité Qdrant
```

---

## Dépendances

```
qdrant-client >= 1.17.1
```

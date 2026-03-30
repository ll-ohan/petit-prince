# embeddings — Encodeur sparse SPLADE V3

Module partagé chargé d'encoder du texte en vecteurs sparse à l'aide du modèle **SPLADE V3** (NAVER). Il est utilisé à la fois par le pipeline d'indexation et par le serveur MCP au moment du retrieval.

---

## Rôle dans l'architecture

```
Indexer  ──┐
            ├──→  SpladeEncoder  ──→  SparseVector  ──→  Qdrant
MCP Server ─┘
```

Le module n'expose pas de serveur HTTP : c'est une bibliothèque Python importée directement par les modules qui en ont besoin.

---

## Fonctionnement

SPLADE V3 est un modèle d'encodage **asymétrique** basé sur BERT. Il produit des vecteurs *sparse* (creux) : au lieu d'un vecteur dense de 768 dimensions, chaque texte est représenté par une liste de paires `(token_id, poids)`, uniquement pour les tokens ayant un poids significatif.

L'asymétrie signifie que l'encodage d'un **document** et celui d'une **requête** utilisent des stratégies différentes pour maximiser la qualité du retrieval.

Une caractéristique importante de SPLADE est l'**expansion lexicale** : le modèle peut attribuer un poids à des tokens qui n'apparaissent pas littéralement dans le texte, mais qui sont sémantiquement liés (ex : « rose » → poids sur « fleur », « unique », « aimer »).

---

## Interface

```python
from embeddings.sparse.encoder import SpladeEncoder
from embeddings.sparse.models import SparseVector

encoder = SpladeEncoder(model_name="naver/splade-v3", device="cpu")

# Encodage d'un passage du livre (indexation)
doc_vec: SparseVector = encoder.encode_document("Il me faut subir deux ou trois chenilles...")

# Encodage d'une requête utilisateur (retrieval)
query_vec: SparseVector = encoder.encode_query("la rose et le renard")

# Encodage en batch (plus efficace pour l'indexation)
vectors: list[SparseVector] = encoder.encode_batch(
    ["texte 1", "texte 2"],
    mode="doc"
)
```

### `SparseVector`

```python
@dataclass
class SparseVector:
    indices: list[int]   # token IDs (vocabulaire BERT, ~30 522 tokens)
    values: list[float]  # poids SPLADE associés
```

Les poids inférieurs à `SPLADE_WEIGHT_THRESHOLD` (0.005 par défaut) sont élagués pour réduire la taille des vecteurs.

---

## Structure

```
embeddings/
├── pyproject.toml
└── src/embeddings/
    ├── __init__.py
    └── sparse/
        ├── __init__.py
        ├── encoder.py     # SpladeEncoder
        └── models.py      # SparseVector
```

---

## Configuration

| Variable d'environnement | Valeur par défaut | Description |
|---|---|---|
| `SPLADE_MODEL` | `naver/splade-v3` | Identifiant HuggingFace du modèle |
| `SPLADE_DEVICE` | `cpu` | Device PyTorch (`cpu`, `cuda`, `mps`) |
| `SPLADE_WEIGHT_THRESHOLD` | `0.005` | Seuil d'élagage des poids faibles |
| `HF_TOKEN` | — | Token HuggingFace (requis pour télécharger le modèle) |

La détection automatique du device peut être activée via `EMBEDDINGS_DEVICE_AUTO=true`, auquel cas le module teste dans l'ordre CUDA → MPS → CPU.

---

## Dépendances

```
sentence-transformers >= 5.3.0
torch >= 2.11.0
numpy >= 2.4.3
```

---

## Notes d'implémentation

- Le modèle est chargé une seule fois à l'instanciation de `SpladeEncoder` et réutilisé pour tous les encodages.
- Le module supprime les avertissements PyTorch liés aux threads de conversion automatique, qui ne sont pas pertinents pour ce cas d'usage.
- En mode batch, les textes sont encodés par lots pour éviter les pics mémoire lors de l'indexation d'un corpus entier.

# indexer — Pipeline d'indexation

Module CLI chargé de lire le texte du *Petit Prince*, de le découper en chunks, de les encoder avec SPLADE V3 et de les upserter dans la collection Qdrant. Ce pipeline est conçu pour être exécuté en one-shot lors de la mise en place initiale, et peut être relancé de façon idempotente.

---

## Rôle dans l'architecture

```
data/le_petit_prince.txt
        │
        ▼
   [loader.py]          lecture + segmentation par page / chapitre
        │
        ▼
   [chunker.py]         découpe en chunks de ~300 tokens avec overlap
        │
        ▼
   [SpladeEncoder]      encodage sparse (via module embeddings)
        │
        ▼
   [qdrant_manager]     upsert dans la collection "petit_prince"
```

---

## Utilisation

```bash
# Indexation complète (réinitialise la collection)
python -m indexer --source data/le_petit_prince.txt --reset

# Simulation sans écriture dans Qdrant
python -m indexer --source data/le_petit_prince.txt --dry-run

# Personnaliser la taille des batchs d'encodage
python -m indexer --source data/le_petit_prince.txt --batch-size 16
```

### Options

| Option | Description |
|--------|-------------|
| `--source` | Chemin vers le fichier texte source (obligatoire) |
| `--reset` | Supprime et recrée la collection Qdrant avant d'indexer |
| `--dry-run` | Affiche les chunks sans écrire dans Qdrant |
| `--batch-size N` | Nombre de chunks encodés en parallèle (défaut : 32) |

---

## Format du fichier source

Le loader attend un fichier texte avec les conventions suivantes :

- Les pages sont séparées par `---`
- Les chapitres sont marqués par une ligne commençant par `CHAPITRE` (ex : `CHAPITRE I`, `CHAPITRE XXI`)

```
CHAPITRE I

Lorsque j'avais six ans...

---

...j'aurais préféré commencer.

---

CHAPITRE II

J'ai ainsi vécu seul...
```

---

## Stratégie de chunking

Le texte est découpé en chunks à l'aide du **tokenizer BERT** (celui de SPLADE), ce qui garantit une cohérence entre la taille de chunk et la capacité du modèle d'encodage.

| Paramètre | Valeur par défaut |
|-----------|-------------------|
| Taille cible | 300 tokens |
| Overlap | 50 tokens |
| Frontières préférées | fins de phrase (`.`) puis fins de paragraphe |

Chaque chunk conserve ses métadonnées d'origine : `chapter_id`, `page_start`, `page_end`, `chunk_index`.

---

## Idempotence

Chaque chunk est identifié par un hash SHA-256 de son contenu. L'ID Qdrant est un UUID v5 dérivé de ce hash. Relancer le pipeline sur un corpus inchangé ne produit donc pas de doublons — les points existants sont simplement mis à jour (upsert).

---

## Structure

```
indexer/
├── pyproject.toml
└── src/indexer/
    ├── __init__.py
    ├── main.py          # Point d'entrée CLI (argparse)
    ├── models.py        # RawPage, Chunk, IndexedChunk, IndexingReport
    └── pipeline/
        ├── __init__.py
        ├── loader.py    # Lecture du fichier texte → list[RawPage]
        └── chunker.py   # Découpe en tokens avec overlap → list[Chunk]
```

---

## Payload Qdrant

Chaque point indexé a la structure suivante :

```json
{
  "id": "uuid-v5-from-hash",
  "vector": {
    "splade": { "indices": [...], "values": [...] }
  },
  "payload": {
    "text": "On ne voit bien qu'avec le cœur...",
    "chapter_id": 21,
    "page_start": 72,
    "page_end": 72,
    "chunk_index": 3,
    "source": "le_petit_prince",
    "content_hash": "sha256:..."
  }
}
```

---

## Rapport d'indexation

À la fin du pipeline, un `IndexingReport` est affiché :

```
Indexation terminée.
  Total chunks   : 187
  Indexés        : 185
  Ignorés (skip) : 2
  Erreurs        : 0
```

---

## Dépendances

Ce module dépend de :
- `embeddings` (workspace local) — pour l'encodage SPLADE
- `qdrant_manager` (workspace local) — pour l'upsert

```
embeddings @ ../embeddings
qdrant_manager @ ../qdrant_manager
```

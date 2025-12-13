# Le Petit Prince RAG Pipeline

Système RAG (Retrieval-Augmented Generation) spécialisé dans "Le Petit Prince" d'Antoine de Saint-Exupéry.

## Architecture

Architecture SOLID en Python avec FastAPI, communicant avec llama.cpp (embeddings, reranking, génération) et Qdrant (vector store).

## Installation

### Prérequis

- Python 3.11+
- llama.cpp server en cours d'exécution
- Qdrant en cours d'exécution
- Fichier texte du Petit Prince dans `var/data/book.txt`

### Installation locale

```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Copier et configurer les variables d'environnement
cp .env.example .env
# Éditer .env selon votre configuration
```

### Configuration

La configuration suit la priorité : **ENV > .env > config.yml**

Éditer [config.yml](config.yml) pour les valeurs par défaut.

## Utilisation

### Démarrer le serveur

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Indexer le livre

```bash
curl -X POST http://localhost:8000/api/init
```

### Chat (mode bloquant)

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Qui est le petit prince?"}
    ]
  }'
```

### Chat (mode streaming)

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -N \
  -d '{
    "messages": [
      {"role": "user", "content": "Qui est le renard?"}
    ],
    "stream": true
  }'
```

### Métriques étendues

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Include-Metrics: true" \
  -d '{
    "messages": [
      {"role": "user", "content": "Quelle est la leçon du renard?"}
    ]
  }'
```

## Tests

```bash
# Tests unitaires
pytest tests/unit -v

# Tests d'intégration (nécessite les services)
pytest tests/integration -v

# Coverage
pytest --cov=src --cov-report=html
```

## Docker

```bash
# Build et démarrage
docker-compose up -d

# Logs
docker-compose logs -f petit-prince-rag

# Arrêt
docker-compose down
```

## Interface Web

Une interface web minimaliste est disponible sur http://localhost après le démarrage avec Docker Compose.

**Fonctionnalités :**
- 💬 Chat interactif avec streaming en temps réel
- 📊 Métriques de performance et visualisation des sources
- 🔧 Configuration de l'API en temps réel
- 🗑️ Gestion de la conversation (sauvegarde locale)
- 🔄 Initialisation de l'index depuis l'interface
- 🌓 Mode debug avec informations détaillées

**Technologies :** HTML/CSS/JavaScript vanilla (zéro dépendances)

## Structure du projet

Voir [CLAUDE.md](CLAUDE.md) pour la documentation complète de l'architecture.

## Endpoints

- `GET /health` - Health check
- `POST /api/init` - Réindexation
- `POST /api/v1/chat/completions` - Chat (compatible OpenAI)

## License

MIT

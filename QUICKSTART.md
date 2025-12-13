# Démarrage Rapide - Le Petit Prince RAG

## 🚀 Installation Express

### 1. Prérequis
- Python 3.11+
- llama.cpp server opérationnel
- Qdrant opérationnel
- Le texte du Petit Prince dans `var/data/book.txt`

### 2. Installation

```bash
# Clone ou navigue vers le projet
cd petit-prince

# Démarrage automatique (crée venv, installe dépendances, lance serveur)
./scripts/start.sh
```

Ou manuellement :

```bash
# Environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Dépendances
pip install -r requirements.txt

# Lancer le serveur
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Configuration

Éditer [config.yml](config.yml) ou créer un fichier `.env` :

```bash
cp .env.example .env
```

Variables importantes :
- `LLAMA__BASE_URL` - URL du serveur llama.cpp
- `QDRANT__HOST` - Hôte Qdrant
- `LOGGING__LEVEL` - Niveau de logs (DEBUG, INFO, WARNING, ERROR)

### 4. Interface Web (Recommandé)

Démarrez l'interface web pour une expérience utilisateur complète :

```bash
# En développement
make frontend

# Ou manuellement
./scripts/serve_frontend.sh
```

Puis ouvrez http://localhost:8080

**Fonctionnalités de l'interface :**
- Chat interactif avec streaming
- Visualisation des métriques et sources
- Initialisation de l'index en un clic
- Configuration de l'API en temps réel

### 5. Indexation

Via l'interface web (bouton "Initialiser") ou en ligne de commande :

```bash
curl -X POST http://localhost:8000/api/init
```

Ou utilisez l'interface Swagger : http://localhost:8000/docs

### 6. Première requête (CLI)

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Qui est le petit prince et d'\''où vient-il?"}
    ]
  }'
```

## 🐳 Docker (Recommandé)

```bash
# Démarrage complet (RAG + Qdrant + llama.cpp)
docker-compose up -d

# Vérifier les logs
docker-compose logs -f petit-prince-rag

# Arrêt
docker-compose down
```

**Note** : Configurez le service `llama-cpp` dans [docker-compose.yml](docker-compose.yml) selon votre setup.

## 📊 Tests

```bash
# Tests unitaires
make test

# Tests avec coverage
make test-cov

# Tests d'intégration (nécessite services actifs)
make test-integration
```

## 🔍 Endpoints disponibles

- **GET** `/health` - Health check
- **GET** `/docs` - Documentation Swagger
- **POST** `/api/init` - Réindexation complète
- **POST** `/api/v1/chat/completions` - Chat RAG (OpenAI-compatible)

## 💡 Exemples d'utilisation

### Chat simple

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Quelle est la leçon du renard?"}
    ]
  }'
```

### Chat avec streaming

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -N \
  -d '{
    "messages": [
      {"role": "user", "content": "Parle-moi de la rose"}
    ],
    "stream": true
  }'
```

### Chat avec métriques étendues

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Include-Metrics: true" \
  -d '{
    "messages": [
      {"role": "user", "content": "Que symbolise le désert?"}
    ]
  }'
```

### Conversation multi-tours

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Qui est le renard?"},
      {"role": "assistant", "content": "Le renard est..."},
      {"role": "user", "content": "Et que lui apprend-il?"}
    ]
  }'
```

## 🛠️ Commandes Make

```bash
make help           # Affiche l'aide
make install        # Installe les dépendances
make run            # Lance le serveur (mode dev avec reload)
make test           # Tests unitaires
make test-cov       # Tests avec coverage
make docker-build   # Build l'image Docker
make docker-up      # Lance avec Docker Compose
make docker-down    # Arrête Docker Compose
make clean          # Nettoie les fichiers temporaires
```

## 🔧 Troubleshooting

### Le serveur ne démarre pas
- Vérifiez que Python 3.11+ est installé : `python3 --version`
- Vérifiez les dépendances : `pip install -r requirements.txt`
- Vérifiez les logs : `tail -f logs/app.log`

### Erreur de connexion à llama.cpp
- Vérifiez que llama.cpp est en cours d'exécution
- Vérifiez l'URL dans `config.yml` ou `LLAMA__BASE_URL`
- Testez manuellement : `curl http://localhost:8080/health`

### Erreur de connexion à Qdrant
- Vérifiez que Qdrant est en cours d'exécution
- Vérifiez l'hôte/port dans `config.yml`
- Testez manuellement : `curl http://localhost:6333`

### Pas de résultats lors de la recherche
- Exécutez `/api/init` pour indexer le livre
- Vérifiez que `var/data/book.txt` existe et contient du texte
- Vérifiez les logs pour des erreurs d'indexation

## 📚 Documentation complète

Voir [CLAUDE.md](CLAUDE.md) pour :
- Architecture détaillée
- Principes SOLID appliqués
- Configuration avancée
- Tests approfondis
- Edge cases et robustesse

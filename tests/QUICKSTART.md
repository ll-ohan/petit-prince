# Quick Start - Tests Le Petit Prince RAG

## Installation des dépendances de test

```bash
# Installer les dépendances de test
pip install -r requirements-test.txt

# Ou avec l'environnement virtuel
source .venv/bin/activate
pip install -r requirements-test.txt
```

## Exécuter les tests

### Tous les tests
```bash
pytest
```

### Tests unitaires uniquement (rapides, pas de services externes)
```bash
pytest -m unit
```

### Tests avec rapport de couverture
```bash
pytest --cov=src --cov-report=html --cov-report=term-missing
```

### Tests en parallèle (plus rapide)
```bash
pytest -n auto
```

### Tests spécifiques par module
```bash
# Configuration
pytest tests/unit/test_config/

# Ingestion
pytest tests/unit/test_ingestion/

# API
pytest tests/unit/test_api/

# Intégration (nécessite services)
pytest tests/integration/
```

## Mur de Qualité (Quality Wall)

Exécuter dans cet ordre avant chaque commit :

```bash
# 1. Formatage automatique
black src/ tests/

# 2. Linting + fixes automatiques
ruff check --fix src/ tests/

# 3. Vérification des types
mypy src/

# 4. Tests (seulement si 1-3 passent)
pytest
```

Script automatique :
```bash
#!/bin/bash
set -e

echo "🎨 Running Black..."
black src/ tests/

echo "🔍 Running Ruff..."
ruff check --fix src/ tests/

echo "📝 Running Mypy..."
mypy src/

echo "✅ Running Tests..."
pytest

echo "🎉 Quality wall passed!"
```

## Markers pytest disponibles

```bash
# Tests unitaires seulement
pytest -m unit

# Tests d'intégration seulement
pytest -m integration

# Tests de cas limites
pytest -m edge_case

# Tests de performance
pytest -m performance

# Exclure les tests lents
pytest -m "not slow"

# Exclure les tests nécessitant des services
pytest -m "not (requires_qdrant or requires_llama)"
```

## Rapport de couverture

Après `pytest --cov=src --cov-report=html` :

```bash
# Ouvrir le rapport HTML
open htmlcov/index.html
```

## Analyse profonde (optionnel)

```bash
# Pylint - analyse sémantique
pylint src/

# Complexité cyclomatique
pip install radon
radon cc src/ -a -nb

# Métriques de maintenabilité
radon mi src/
```

## CI/CD Integration

Exemple GitHub Actions :

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run quality checks
        run: |
          black --check src/ tests/
          ruff check src/ tests/
          mypy src/

      - name: Run tests
        run: |
          pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Structure des tests

```
tests/
├── conftest.py              # Fixtures globales
├── pytest.ini               # Configuration pytest
├── unit/                    # Tests isolés (mocks)
│   ├── test_config/
│   ├── test_utils/
│   ├── test_ingestion/
│   ├── test_infrastructure/
│   ├── test_generation/
│   └── test_api/
└── integration/             # Tests end-to-end
    └── test_pipeline.py
```

## Fixtures principales

Voir [conftest.py](conftest.py) pour la liste complète.

**Fichiers:**
- `temp_dir` : Répertoire temporaire
- `sample_text_file` : Texte Le Petit Prince
- `empty_file`, `whitespace_only_file`, `noise_only_file`

**Configuration:**
- `valid_config_dict` : Config complète
- `config_yaml_file` : Fichier YAML valide

**Mocks:**
- `mock_httpx_client` : Client HTTP mocké
- `mock_qdrant_client` : Client Qdrant mocké
- `mock_embedder`, `mock_reranker`, `mock_generator`

**Données:**
- `sample_sentences`, `sample_paragraphs`
- `sample_embeddings` : Vecteurs de test

## Debugging tests

```bash
# Mode verbeux
pytest -vv

# Arrêt au premier échec
pytest -x

# Dernière exécution échouée
pytest --lf

# Trace complète
pytest --tb=long

# Debug avec pdb
pytest --pdb

# Logs visibles
pytest --log-cli-level=DEBUG
```

## Troubleshooting

### Import errors
```bash
# S'assurer que PYTHONPATH inclut src/
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
pytest
```

### Tests lents
```bash
# Identifier les tests lents
pytest --durations=10
```

### Services non disponibles
```bash
# Skip les tests nécessitant des services
pytest -m "not (requires_qdrant or requires_llama)"
```

## Ressources

- [README.md](README.md) - Documentation complète des tests
- [CLAUDE.md](../CLAUDE.md) - Spécifications du projet
- [pytest documentation](https://docs.pytest.org/)

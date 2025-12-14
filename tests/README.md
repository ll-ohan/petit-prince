# Tests Documentation - Le Petit Prince RAG

## Vue d'ensemble

Cette suite de tests implémente le plan de test complet défini dans [CLAUDE.md](../CLAUDE.md#9-testing).

## Structure des tests

```
tests/
├── conftest.py                      # Fixtures globales et configuration
├── pytest.ini                       # Configuration pytest
├── unit/                            # Tests unitaires (isolés, rapides)
│   ├── test_config/
│   │   ├── test_settings_valid.py   ✅ IMPLÉMENTÉ
│   │   └── test_settings_invalid.py ✅ IMPLÉMENTÉ
│   ├── test_utils/
│   │   └── test_batch.py            ✅ IMPLÉMENTÉ
│   ├── test_ingestion/
│   │   ├── test_reader.py           ✅ IMPLÉMENTÉ
│   │   ├── test_chunker.py          📝 À IMPLÉMENTER
│   │   ├── test_paragraph_builder.py📝 À IMPLÉMENTER
│   │   └── test_service.py          📝 À IMPLÉMENTER
│   ├── test_infrastructure/
│   │   ├── test_llama_client.py     📝 À IMPLÉMENTER
│   │   └── test_qdrant_client.py    📝 À IMPLÉMENTER
│   ├── test_generation/
│   │   ├── test_prompt_builder.py   📝 À IMPLÉMENTER
│   │   ├── test_response_handler.py 📝 À IMPLÉMENTER
│   │   └── test_service.py          📝 À IMPLÉMENTER
│   └── test_api/
│       ├── test_init_route.py       📝 À IMPLÉMENTER
│       └── test_chat_route.py       📝 À IMPLÉMENTER
├── integration/                     # Tests d'intégration
│   ├── test_pipeline.py             📝 À IMPLÉMENTER
│   └── test_api_endpoints.py        📝 À IMPLÉMENTER
└── fixtures/                        # Données de test
    ├── config_samples/
    ├── text_samples/
    └── expected_outputs/
```

## Tests implémentés (✅)

### 1. Configuration Layer (`test_config/`)

#### `test_settings_valid.py`
- ✅ Test création configs valides pour chaque modèle
- ✅ Test valeurs par défaut
- ✅ Test chargement depuis YAML
- ✅ Test priorité ENV > .env > YAML
- ✅ Test fusion partielle YAML + defaults

**Coverage**: 100% des cas nominaux

#### `test_settings_invalid.py`
- ✅ Test URLs invalides (non HTTP/HTTPS)
- ✅ Test dimensions d'embedding hors limites (≤0, >8192)
- ✅ Test batch_size invalide
- ✅ Test timeout invalide
- ✅ Test ports invalides
- ✅ Test noms de collection invalides
- ✅ Test top_x > top_k
- ✅ Test fichiers manquants
- ✅ Test YAML malformé
- ✅ Test types invalides

**Coverage**: 100% des edge cases

### 2. Utilities Layer (`test_utils/`)

#### `test_batch.py`
- ✅ Test division exacte
- ✅ Test avec reste
- ✅ Test liste vide
- ✅ Test batch_size > longueur liste
- ✅ Test batch_size ≤ 0 (erreur)
- ✅ Test préservation de l'ordre
- ✅ Test préservation de l'identité des objets
- ✅ Test performance (benchmark)

**Coverage**: 100% + performance tests

### 3. Ingestion Layer (`test_ingestion/`)

#### `test_reader.py`
- ✅ Test lecture UTF-8
- ✅ Test lecture avec encodages alternatifs (Latin-1, CP1252)
- ✅ Test fichier inexistant (erreur)
- ✅ Test fichier vide (erreur)
- ✅ Test whitespace seulement (erreur)
- ✅ Test fichier binaire (erreur gracieuse)
- ✅ Test caractères Unicode/emoji
- ✅ Test fichiers volumineux (1MB+)
- ✅ Test logging approprié

**Coverage**: 100% des scénarios TextReader

## Tests à implémenter (📝)

### 3. Ingestion Layer (suite)

#### `test_chunker.py` - **PRIORITAIRE**
Tests requis selon CLAUDE.md section 9.2:

**Cas Nominaux:**
- [ ] `test_chunk_simple_sentences`: Découpage standard
- [ ] `test_chunk_dialogue`: Gestion guillemets et tirets
- [ ] `test_chunk_ellipsis`: Ne pas couper sur "..."

**Cas Limites:**
- [ ] `test_chunk_empty_text`: Retourne liste vide
- [ ] `test_chunk_noise_filtering`: Filtre "Chapitre I", "IV", "1."
- [ ] `test_chunk_very_long_sentence`: >1000 caractères (warning)
- [ ] `test_chunk_no_valid_sentences`: Seulement du bruit → IngestionError

**Implémentation suggérée:**
```python
@pytest.mark.unit
class TestSentenceChunkerNominal:
    def test_chunk_simple_sentences(self):
        chunker = SentenceChunker(language="fr")
        text = "Le Petit Prince habitait une planète. Il avait une rose."
        sentences = chunker.chunk(text)

        assert len(sentences) == 2
        assert sentences[0].strip() == "Le Petit Prince habitait une planète."
        assert sentences[1].strip() == "Il avait une rose."
```

#### `test_paragraph_builder.py`
**Cas Nominaux:**
- [ ] `test_build_paragraphs_exact_count`: Grouper exactement N phrases
- [ ] `test_build_paragraphs_with_remainder`: Dernier paragraphe < N phrases

**Cas Limites:**
- [ ] `test_build_empty_input`: Liste vide → liste vide
- [ ] `test_build_sentences_fewer_than_chunk_size`: Un seul paragraphe

#### `test_service.py` (IngestionService)
**Nécessite mocks pour Reader, Chunker, Embedder, VectorStore**

**Cas Nominaux:**
- [ ] `test_ingest_full_pipeline_success`: Read → Chunk → Build → Embed → Upsert
- [ ] `test_ingest_returns_statistics`: Vérifier stats (nb docs, temps, etc.)

**Cas Limites:**
- [ ] `test_ingest_embedder_failure`: Propagation EmbeddingError
- [ ] `test_ingest_vectorstore_failure`: Propagation VectorStoreError

### 4. Infrastructure Layer

#### `test_llama_client.py` - **CRITIQUE**
**Nécessite pytest-httpx pour mocker httpx**

**Cas Nominaux:**
- [ ] `test_embed_batch_success`: Retourne vecteurs dimension correcte
- [ ] `test_rerank_success`: Retourne docs triés avec scores
- [ ] `test_generate_blocking_success`: Retourne texte généré
- [ ] `test_generate_streaming_success`: Retourne itérateur chunks

**Cas Limites:**
- [ ] `test_embed_dimension_mismatch`: config.dim ≠ réponse → erreur
- [ ] `test_embed_api_timeout`: Retry puis erreur
- [ ] `test_embed_api_500_error`: Retry puis EmbeddingError
- [ ] `test_embed_nan_values`: Vecteur avec NaN/Inf → erreur
- [ ] `test_generate_empty_response`: Gestion chaîne vide

**Exemple mock httpx:**
```python
@pytest.mark.asyncio
async def test_embed_batch_success(respx_mock):
    respx_mock.post("http://localhost:8080/v1/embeddings").mock(
        return_value=httpx.Response(200, json={
            "data": [{"embedding": [0.1] * 1024}]
        })
    )

    client = LlamaClient(config)
    vectors = await client.embed_batch(["test"])

    assert len(vectors) == 1
    assert len(vectors[0]) == 1024
```

#### `test_qdrant_client.py`
**Nécessite mock AsyncQdrantClient**

**Cas Nominaux:**
- [ ] `test_create_collection_idempotency`: Supprime puis crée
- [ ] `test_upsert_vectors`: Points structurés correctement
- [ ] `test_search_vectors`: Mapping SearchResult correct

**Cas Limites:**
- [ ] `test_upsert_mismatch_count`: len(texts) ≠ len(vectors) → erreur
- [ ] `test_search_connection_error`: Qdrant injoignable → VectorStoreError
- [ ] `test_create_collection_failure`: Erreur API → VectorStoreError

### 5. Generation Layer

#### `test_prompt_builder.py` - **PRIORITAIRE**

**Cas Nominaux:**
- [ ] `test_build_prompt_high_relevance`: Tous scores ≥ seuil → SYSTEM_PROMPT_ALL_RELEVANT
- [ ] `test_build_prompt_mixed_relevance`: Mix scores → SYSTEM_PROMPT_PARTIAL
- [ ] `test_build_prompt_low_relevance`: Tous < seuil → SYSTEM_PROMPT_LOW_RELEVANCE
- [ ] `test_context_injection_format`: Tags [PERTINENCE: HAUTE/MODÉRÉE]

**Cas Limites:**
- [ ] `test_build_prompt_no_documents`: Liste vide → low relevance
- [ ] `test_build_prompt_history_preservation`: Historique conversation intact

#### `test_response_handler.py`

**Cas Nominaux:**
- [ ] `test_format_blocking_response`: Schéma OpenAI correct
- [ ] `test_format_streaming_chunks`: Format SSE correct
- [ ] `test_extended_metrics_inclusion`: x_metrics si header

**Cas Limites:**
- [ ] `test_format_usage_calculation`: total = prompt + completion

#### `test_service.py` (GenerationService)

**Cas Nominaux:**
- [ ] `test_process_query_standard_flow`: Embed → Search → Rerank → Prompt

**Cas Limites:**
- [ ] `test_process_query_no_search_results`: Arrêt après search
- [ ] `test_process_query_reranker_failure`: Fallback vector search
- [ ] `test_token_counting_failure`: Estimation si échec count_tokens

### 6. API Layer

#### `test_init_route.py` - **CRITIQUE**

**Cas Nominaux:**
- [ ] `test_api_init_success`: Retourne 200 + stats

**Erreurs:**
- [ ] `test_api_init_ingestion_error_422`: Fichier vide → 422
- [ ] `test_api_init_vectorstore_error_500`: Qdrant down → 500
- [ ] `test_api_init_unexpected_error_500`: Exception → 500

#### `test_chat_route.py` - **CRITIQUE**

**Cas Nominaux:**
- [ ] `test_api_chat_blocking_success`: JSON complet
- [ ] `test_api_chat_streaming_success`: StreamingResponse SSE
- [ ] `test_api_chat_with_metrics_header`: x_metrics inclus

**Erreurs:**
- [ ] `test_api_chat_empty_messages`: 422
- [ ] `test_api_chat_validation_error_422`: Payload invalide
- [ ] `test_api_chat_retrieval_error_503`: Qdrant down → 503
- [ ] `test_api_chat_generation_error_503`: LLM timeout → 503
- [ ] `test_api_chat_internal_error_500`: Crash inattendu
- [ ] `test_api_chat_streaming_disconnect`: Client déconnecte → cleanup

### 7. Integration Tests

#### `test_pipeline.py` - **END-TO-END**

**Avec mocks:**
- [ ] `test_indexing`: POST /api/init avec mock
- [ ] `test_reindexing`: Double init → pas de duplication
- [ ] `test_generate`: Chat avec docs mockés → citation dans réponse

**Sans mocks (requires external services):**
- [ ] `test_init`: Ingestion réelle → vérif Qdrant
- [ ] `test_chat`: Requête réelle → réponse valide
- [ ] `test_chat_concurrence`: Requêtes parallèles

#### `test_api_endpoints.py`
- [ ] `test_health_endpoint`: GET /health → 200
- [ ] `test_cors_headers`: Vérif headers CORS
- [ ] `test_rate_limiting`: Si implémenté

## Markers pytest

```python
@pytest.mark.unit           # Test unitaire isolé
@pytest.mark.integration    # Test d'intégration
@pytest.mark.edge_case      # Cas limite / erreur
@pytest.mark.performance    # Test performance
@pytest.mark.slow           # Test lent (>1s)
@pytest.mark.requires_qdrant    # Nécessite Qdrant running
@pytest.mark.requires_llama     # Nécessite llama.cpp running
@pytest.mark.requires_all_services  # Tous les services
```

## Exécution des tests

### Tests unitaires uniquement (rapides)
```bash
pytest -m unit
```

### Tests avec coverage
```bash
pytest --cov=src --cov-report=html
```

### Tests parallèles
```bash
pytest -n auto
```

### Tests spécifiques
```bash
# Configuration seulement
pytest tests/unit/test_config/

# Sans services externes
pytest -m "unit and not (requires_qdrant or requires_llama)"

# Intégration seulement
pytest -m integration
```

## Métriques de qualité

### Objectifs de coverage
- **Global**: ≥ 80%
- **Core business logic**: ≥ 90%
- **Configuration**: 100%
- **Error handling**: 100%

### Exécution du "Mur de Qualité"
Comme défini dans CLAUDE.md section 2.6:

```bash
# 1. Black (formatage)
black src/ tests/

# 2. Ruff (linting + fix)
ruff check --fix src/ tests/

# 3. Mypy (type checking)
mypy src/

# 4. Tests (seulement si 1-3 passent)
pytest
```

### Analyse profonde (optionnel)
```bash
# Pylint pour analyse sémantique
pylint src/

# Complexité cyclomatique
radon cc src/ -a -nb
```

## Fixtures disponibles

Voir [conftest.py](conftest.py) pour la liste complète.

**Principales fixtures:**
- `temp_dir`: Répertoire temporaire
- `sample_text_file`: Fichier texte Le Petit Prince
- `empty_file`, `whitespace_only_file`, `noise_only_file`
- `valid_config_dict`, `config_yaml_file`
- `sample_sentences`, `sample_paragraphs`, `sample_embeddings`
- `mock_httpx_client`, `mock_qdrant_client`
- `mock_embedder`, `mock_reranker`, `mock_generator`

## Bonnes pratiques

1. **Docstrings obligatoires** sur chaque test
2. **Assertions spécifiques** (pas juste `assert result`)
3. **Arrange-Act-Assert** pattern
4. **Un concept par test**
5. **Noms descriptifs** (`test_what_when_then`)
6. **Parametrize** pour variantes multiples
7. **Context preservation** dans exceptions

## Contribution

Pour ajouter des tests:

1. Identifier le composant à tester
2. Lire la spec dans CLAUDE.md section 9
3. Créer fichier `test_<component>.py`
4. Implémenter cas nominaux puis edge cases
5. Vérifier coverage: `pytest --cov-report=term-missing`
6. Exécuter quality wall avant commit

## Ressources

- [CLAUDE.md](../CLAUDE.md) - Spécifications complètes
- [pytest docs](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-httpx](https://colin-b.github.io/pytest_httpx/)

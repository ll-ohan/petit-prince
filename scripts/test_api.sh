#!/bin/bash

# Script de test de l'API Le Petit Prince RAG

set -e

API_URL="${API_URL:-http://localhost:8000}"

echo "🧪 Test de l'API Le Petit Prince RAG"
echo "===================================="
echo "API URL: $API_URL"
echo ""

# Test health
echo "1️⃣  Test du health check..."
curl -s "$API_URL/health" | jq '.' || echo "❌ Health check échoué"
echo ""

# Test init (optionnel)
if [ "$1" == "--init" ]; then
    echo "2️⃣  Initialisation de l'index..."
    curl -s -X POST "$API_URL/api/init" | jq '.' || echo "❌ Init échoué"
    echo ""
fi

# Test chat bloquant
echo "3️⃣  Test chat (mode bloquant)..."
curl -s -X POST "$API_URL/api/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
        "messages": [
            {"role": "user", "content": "Qui est le petit prince?"}
        ],
        "stream": false
    }' | jq '.choices[0].message.content' || echo "❌ Chat échoué"
echo ""

# Test chat avec métriques
echo "4️⃣  Test chat avec métriques..."
curl -s -X POST "$API_URL/api/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -H "X-Include-Metrics: true" \
    -d '{
        "messages": [
            {"role": "user", "content": "Que représente le renard?"}
        ],
        "stream": false
    }' | jq '.x_metrics' || echo "❌ Métriques non disponibles"
echo ""

# Test chat streaming
echo "5️⃣  Test chat (mode streaming)..."
curl -s -N -X POST "$API_URL/api/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
        "messages": [
            {"role": "user", "content": "Quelle est la leçon du renard?"}
        ],
        "stream": true
    }' | head -20 || echo "❌ Streaming échoué"
echo ""

echo "✅ Tests terminés"

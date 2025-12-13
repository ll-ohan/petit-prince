#!/bin/bash

# Script pour servir l'interface frontend en développement

set -e

echo "🌐 Le Petit Prince - Serveur Frontend Local"
echo "==========================================="

cd "$(dirname "$0")/.."

# Vérifier que le dossier frontend existe
if [ ! -d "frontend" ]; then
    echo "❌ Dossier frontend introuvable"
    exit 1
fi

# Vérifier Python
if command -v python3 &> /dev/null; then
    echo "📡 Démarrage du serveur Python sur http://localhost:8080"
    echo "   Interface disponible sur http://localhost:8080"
    echo ""
    echo "⚠️  Note: Configure l'URL de l'API dans l'interface si elle n'est pas sur localhost:8000"
    echo ""
    cd frontend
    python3 -m http.server 8080
elif command -v python &> /dev/null; then
    echo "📡 Démarrage du serveur Python sur http://localhost:8080"
    cd frontend
    python -m SimpleHTTPServer 8080
elif command -v php &> /dev/null; then
    echo "📡 Démarrage du serveur PHP sur http://localhost:8080"
    php -S localhost:8080 -t frontend
else
    echo "❌ Aucun serveur HTTP trouvé (Python ou PHP requis)"
    echo ""
    echo "Alternatives :"
    echo "  - Installer Python : https://www.python.org"
    echo "  - Utiliser npx serve : npx serve frontend"
    echo "  - Utiliser Docker : docker-compose up frontend"
    exit 1
fi

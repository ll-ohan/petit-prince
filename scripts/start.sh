#!/bin/bash

# Script de démarrage rapide pour Le Petit Prince RAG

set -e

echo "🌟 Le Petit Prince RAG - Démarrage"
echo "=================================="

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    exit 1
fi

# Vérifier l'environnement virtuel
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer l'environnement virtuel
echo "🔧 Activation de l'environnement virtuel..."
source venv/bin/activate

# Installer les dépendances
echo "📥 Installation des dépendances..."
pip install -q -r requirements.txt

# Vérifier le fichier source
if [ ! -f "var/data/book.txt" ]; then
    echo "⚠️  Attention: var/data/book.txt n'existe pas"
    echo "   Placez le texte du Petit Prince dans ce fichier"
fi

# Vérifier la configuration
if [ ! -f "config.yml" ]; then
    echo "❌ config.yml manquant"
    exit 1
fi

# Démarrer le serveur
echo "🚀 Démarrage du serveur..."
echo ""
echo "📍 API disponible sur http://localhost:8000"
echo "📖 Documentation: http://localhost:8000/docs"
echo ""

uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

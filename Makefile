.PHONY: help install test run frontend docker-build docker-up docker-down clean

help:
	@echo "Le Petit Prince RAG - Commandes disponibles:"
	@echo "  make install        - Installer les dépendances"
	@echo "  make test          - Lancer les tests"
	@echo "  make test-cov      - Tests avec coverage"
	@echo "  make run           - Démarrer le serveur backend"
	@echo "  make frontend      - Servir l'interface web (dev)"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-up     - Démarrer avec Docker Compose"
	@echo "  make docker-down   - Arrêter Docker Compose"
	@echo "  make clean         - Nettoyer les fichiers temporaires"

install:
	pip install -r requirements.txt

test:
	pytest tests/unit -v

test-cov:
	pytest --cov=src --cov-report=html --cov-report=term

test-integration:
	pytest tests/integration -v

run:
	uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	./scripts/serve_frontend.sh

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f petit-prince-rag

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov

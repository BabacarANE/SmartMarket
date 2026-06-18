.PHONY: help up down logs test lint dbt-run dbt-test collect retrain init

# Couleurs
GREEN  := \033[0;32m
YELLOW := \033[0;33m
NC     := \033[0m

help: ## Afficher l'aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-15s$(NC) %s\n", $$1, $$2}'

# ─── Infrastructure ──────────────────────────────────────────────────

up: ## Démarrer tous les services
	docker compose up -d
	@echo "$(GREEN)✓ Services démarrés$(NC)"
	@echo "  Airflow  → http://localhost:8080"
	@echo "  MLflow   → http://localhost:5000"
	@echo "  FastAPI  → http://localhost:8000/docs"
	@echo "  Streamlit→ http://localhost:8501"

up-dev: ## Démarrer avec pgAdmin (profil dev)
	docker compose --profile dev up -d

down: ## Arrêter tous les services
	docker compose down

down-v: ## Arrêter et supprimer les volumes (reset complet)
	docker compose down -v
	@echo "$(YELLOW)⚠ Volumes supprimés — données effacées$(NC)"

logs: ## Voir les logs de tous les services
	docker compose logs -f

logs-%: ## Voir les logs d'un service (ex: make logs-fastapi)
	docker compose logs -f $*

build: ## Rebuild les images Docker
	docker compose build --no-cache

# ─── Base de données ─────────────────────────────────────────────────

init-db: ## Initialiser les schémas PostgreSQL manuellement
	docker compose exec postgres psql -U $${POSTGRES_USER} -d $${POSTGRES_DB} -f /docker-entrypoint-initdb.d/init_db.sql

psql: ## Ouvrir un shell PostgreSQL
	docker compose exec postgres psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

# ─── Pipeline ETL ────────────────────────────────────────────────────

collect: ## Lancer une collecte manuelle (France Travail + Adzuna)
	docker compose exec airflow-worker airflow dags trigger etl_daily_pipeline

collect-ft: ## Collecte France Travail uniquement
	docker compose exec airflow-worker python -m ml.collectors.france_travail

# ─── dbt ─────────────────────────────────────────────────────────────

dbt-run: ## Lancer les transformations dbt
	cd dbt && dbt run --profiles-dir .

dbt-test: ## Lancer les tests dbt
	cd dbt && dbt test --profiles-dir .

dbt-compile: ## Compiler dbt (dry-run, utilisé en CI)
	cd dbt && dbt compile --profiles-dir .

dbt-docs: ## Générer et servir la documentation dbt
	cd dbt && dbt docs generate --profiles-dir . && dbt docs serve

# ─── Machine Learning ────────────────────────────────────────────────

retrain: ## Lancer un ré-entraînement manuel
	docker compose exec airflow-worker airflow dags trigger ml_retraining_pipeline

# ─── Tests & Qualité ─────────────────────────────────────────────────

test: ## Lancer les tests unitaires
	pytest tests/ -v --cov=ml --cov=api --cov-report=term-missing

test-cov: ## Lancer les tests avec rapport HTML
	pytest tests/ -v --cov=ml --cov=api --cov-report=html
	@echo "$(GREEN)Rapport → htmlcov/index.html$(NC)"

lint: ## Vérifier le code (ruff + black)
	ruff check .
	black --check .

format: ## Formater le code
	ruff check --fix .
	black .

# ─── Setup initial ───────────────────────────────────────────────────

setup: ## Setup initial du projet (copie .env, install deps)
	@if [ ! -f .env ]; then cp .env.example .env && echo "$(YELLOW)⚠ .env créé — pense à renseigner les clés API$(NC)"; fi
	pip install -r requirements.txt
	@echo "$(GREEN)✓ Setup terminé$(NC)"

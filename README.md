# SmartMarket Intelligence

> Plateforme data end-to-end d'analyse et de prédiction du marché de l'emploi tech en France.

[![CI](https://github.com/BabacarANE/SmartMarket/actions/workflows/ci.yml/badge.svg)](https://github.com/BabacarANE/SmartMarket/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Airflow](https://img.shields.io/badge/Airflow-2.9-red)
![MLflow](https://img.shields.io/badge/MLflow-2.13-orange)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Ce que fait ce projet

SmartMarket collecte automatiquement des offres d'emploi tech depuis les APIs France Travail et Adzuna, les nettoie, les transforme avec dbt, entraîne un modèle LightGBM pour prédire les salaires, et expose le tout via une API REST et un dashboard interactif.
APIs publiques → Airflow → PostgreSQL → dbt → LightGBM → FastAPI → Streamlit

---

## Architecture
┌─────────────────────────────────────────────────────────┐

│                    SOURCES DE DONNÉES                    │

│           France Travail API · Adzuna API                │

└────────────────────┬────────────────────────────────────┘

│ collecte quotidienne (06h00)

▼

┌─────────────────────────────────────────────────────────┐

│              ORCHESTRATION — Apache Airflow              │

│   collect → clean → dbt run → validate                  │

└────────────────────┬────────────────────────────────────┘

│

▼

┌─────────────────────────────────────────────────────────┐

│              STOCKAGE — PostgreSQL + pgvector            │

│   raw.offres_emploi  →  clean.offres  →  analytics.*    │

└────────────────────┬────────────────────────────────────┘

│

▼

┌─────────────────────────────────────────────────────────┐

│           MACHINE LEARNING — LightGBM + MLflow           │

│   Feature Engineering (249 features)                    │

│   MAE = 7 065€ · R² = 0.559 · MAPE = 17.5%             │

└────────────────────┬────────────────────────────────────┘

│

┌──────────┴──────────┐

▼                     ▼

┌──────────────────┐  ┌──────────────────────────┐

│   FastAPI :8000  │  │   Streamlit :8501         │

│   /predict       │  │   Vue Marché              │

│   /trends        │  │   Carte Salaires          │

│   /health        │  │   Prédiction Live         │

└──────────────────┘  │   Monitoring ML           │

└──────────────────────────┘

---

## Stack technique

| Couche | Technologie | Rôle |
|--------|------------|------|
| Orchestration | Apache Airflow 2.9 | Scheduling ETL quotidien |
| Transformation | dbt-core 1.11 | Modélisation SQL (4 modèles) |
| Base de données | PostgreSQL 15 + pgvector | Stockage multi-schémas |
| ML | LightGBM + scikit-learn | Prédiction salaires |
| MLOps | MLflow 2.13 | Tracking + Model Registry |
| API | FastAPI + Uvicorn | Exposition modèle |
| Dashboard | Streamlit + Plotly | Visualisation interactive |
| Infrastructure | Docker Compose | Stack complète en 1 commande |

---

## Démarrage rapide

### Prérequis
- Docker Desktop
- WSL2 Ubuntu (Windows) ou Linux/macOS
- Clés API [France Travail](https://francetravail.io) et [Adzuna](https://developer.adzuna.com)

### Installation

```bash
# 1. Cloner
git clone https://github.com/BabacarANE/SmartMarket.git
cd SmartMarket

# 2. Configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API

# 3. Démarrer tous les services
docker compose up -d

# 4. Initialiser Airflow (première fois uniquement)
docker compose run --rm airflow-init
```

### Services disponibles

| Service | URL | Credentials |
|---------|-----|-------------|
| Airflow | http://localhost:8080 | admin / admin |
| MLflow | http://localhost:5000 | — |
| FastAPI | http://localhost:8000/docs | — |
| Streamlit | http://localhost:8501 | — |

---

## Données & Modèle

### Volume de données
- **5 451 offres** collectées (France Travail + Adzuna)
- **31.7%** avec salaire renseigné → 1 558 exemples d'entraînement
- Collecte automatique quotidienne via Airflow

### Performance du modèle

| Métrique | Valeur | Seuil cible |
|----------|--------|-------------|
| MAE | 7 065€ | < 8 000€ ✅ |
| R² | 0.559 | > 0.5 ✅ |
| MAPE | 17.5% | < 20% ✅ |

### Features utilisées (249 total)
- TF-IDF description (200 features)
- One-hot top-30 technologies
- Encodage région, contrat, expérience
- Indicateurs booléens (remote, technologies clés)

---

## Structure du projet
SmartMarket/

├── airflow/dags/          # DAGs Airflow (ETL quotidien)

├── api/                   # FastAPI (predict, trends, health)

├── dashboard/             # Streamlit (4 pages)

├── dbt/models/            # Modèles dbt (staging + analytics)

├── ml/

│   ├── collectors/        # France Travail + Adzuna collectors

│   ├── features/          # Feature engineering (249 features)

│   └── models/            # Entraînement XGBoost/LightGBM

├── scripts/               # Init PostgreSQL

├── docker-compose.yml     # Stack complète

└── .env.example           # Variables d'environnement

---

## API Reference

### POST /predict

```json
// Request
{
  "titre": "Data Engineer Senior",
  "type_contrat": "CDI",
  "ville": "Paris",
  "niveau_experience": "senior",
  "technologies": ["python", "sql", "aws", "spark"],
  "is_remote": true
}

// Response
{
  "salaire_predit": 58000,
  "intervalle_confiance": [49300, 66700],
  "model_version": "2"
}
```

### GET /trends/technologies
Retourne le top 10 des technologies les plus demandées avec salaire moyen.

### GET /trends/salaries
Retourne le classement des villes par salaire moyen.

---

## Développement

```bash
# Activer l'environnement ML/dbt
source .venv-dbt/bin/activate

# Lancer les tests
pytest tests/ -v --cov=ml

# Lancer dbt
dbt run
dbt test

# Ré-entraîner le modèle
PYTHONPATH=. python3 ml/models/train.py

# Lancer l'API en dev
uvicorn api.main:app --reload --port 8000

# Lancer le dashboard
streamlit run dashboard/app.py
```

---

## Projet académique

Projet personnel M1 — Juin 2026  
Démonstration d'une stack MLOps complète : ETL automatisé, feature engineering, model tracking, API serving, dashboard interactif.

**Contact :** [GitHub](https://github.com/BabacarANE)

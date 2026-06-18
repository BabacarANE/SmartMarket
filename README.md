# SmartMarket Intelligence

> Plateforme data end-to-end d'analyse et de prédiction du marché de l'emploi tech en France.

[![CI](https://github.com/BabacarANE/SmartMarket/actions/workflows/ci.yml/badge.svg)](https://github.com/BabacarANE/SmartMarket/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Status](https://img.shields.io/badge/status-en%20développement-yellow)

---

## Architecture

```
Collecte (France Travail + Adzuna)
    ↓
Nettoyage + dbt (PostgreSQL)
    ↓
Feature Engineering (TF-IDF + Embeddings)
    ↓
Entraînement ML — XGBoost / LightGBM (MLflow)
    ↓
API REST (FastAPI) + Dashboard (Streamlit)
```

## Stack

| Couche | Technologie |
|--------|------------|
| Orchestration | Apache Airflow 2.9 |
| Transformation | dbt-core 1.8 |
| Base de données | PostgreSQL 15 + pgvector |
| ML | XGBoost, LightGBM, scikit-learn |
| MLOps | MLflow 2.13 + Evidently AI |
| API | FastAPI + Uvicorn |
| Dashboard | Streamlit + Plotly |
| Infra | Docker Compose |
| CI/CD | GitHub Actions |

## Démarrage rapide

```bash
# 1. Cloner le repo
git clone https://github.com/BabacarANE/SmartMarket.git
cd SmartMarket

# 2. Configurer l'environnement
make setup   # copie .env.example → .env

# 3. Renseigner les clés API dans .env
#    FRANCE_TRAVAIL_CLIENT_ID, ADZUNA_APP_ID, etc.

# 4. Démarrer tous les services
make up

# Services disponibles :
#   Airflow   → http://localhost:8080
#   MLflow    → http://localhost:5000
#   FastAPI   → http://localhost:8000/docs
#   Streamlit → http://localhost:8501
```

## Développement

```bash
make test      # tests unitaires + couverture
make lint      # ruff + black
make dbt-run   # transformations dbt
make retrain   # ré-entraînement ML manuel
```

## Phases du projet

- [x] **Phase 1** — Fondations & ETL (en cours)
- [ ] **Phase 2** — Orchestration Airflow
- [ ] **Phase 3** — Machine Learning + MLflow
- [ ] **Phase 4** — API & Dashboard
- [ ] **Phase 5** — Qualité & Déploiement

---

*Projet personnel M1 — Juin 2026*

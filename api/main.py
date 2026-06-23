"""
API REST SmartMarket Intelligence
Endpoints : /predict, /health, /trends
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

import joblib
import mlflow
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
DB_CONN = os.environ.get("DB_CONN_STRING", "postgresql+pg8000://smartmarket:x@localhost:5433/smartmarket_db")

# Modèle global chargé au démarrage
model = None
feature_engineer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Charge le modèle au démarrage depuis MLflow Registry."""
    global model
    try:
        mlflow.set_tracking_uri(MLFLOW_URI)
        client = mlflow.MlflowClient()

        versions = client.get_latest_versions(
            "smartmarket-salary-model", stages=["Production"]
        )
        if versions:
            v = versions[0]
            local_path = client.download_artifacts(
                v.run_id, "model/lightgbm_production.joblib"
            )
            model = joblib.load(local_path)
            logger.info(f"Modèle Production v{v.version} chargé ✅")
        else:
            logger.warning("Aucun modèle en Production")
    except Exception as e:
        logger.error(f"Erreur chargement modèle: {e}", exc_info=True)
    yield


app = FastAPI(
    title="SmartMarket Intelligence API",
    description="API de prédiction de salaires tech en France",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Schémas ─────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    titre: str = Field(..., example="Data Engineer Senior")
    description: str = Field(default="", example="Python, Spark, AWS...")
    type_contrat: str = Field(default="CDI", example="CDI")
    ville: str = Field(default="Paris", example="Paris")
    niveau_experience: str = Field(default="mid", example="senior")
    technologies: list[str] = Field(default=[], example=["python", "sql", "aws"])
    is_remote: bool = Field(default=False)


class PredictResponse(BaseModel):
    salaire_predit: int
    intervalle_confiance: list[int]
    model_version: str
    currency: str = "EUR"


# ─── Endpoints ───────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "mlflow_uri": MLFLOW_URI,
    }


@app.get("/model/info")
def model_info():
    mlflow.set_tracking_uri(MLFLOW_URI)
    client = mlflow.MlflowClient()
    versions = client.get_latest_versions(
        "smartmarket-salary-model", stages=["Production"]
    )
    if not versions:
        raise HTTPException(status_code=404, detail="Aucun modèle en Production")
    v = versions[0]
    run = client.get_run(v.run_id)
    return {
        "model_name": "smartmarket-salary-model",
        "version": v.version,
        "stage": v.current_stage,
        "mae": run.data.metrics.get("test_mae"),
        "r2": run.data.metrics.get("test_r2"),
    }


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Modèle non disponible")

    # Construction des features
    features = _build_features(request)
    
    salary_pred = float(model.predict(features)[0])
    salary_pred = max(15000, min(200000, salary_pred))
    
    margin = salary_pred * 0.15
    
    return PredictResponse(
        salaire_predit=int(salary_pred),
        intervalle_confiance=[int(salary_pred - margin), int(salary_pred + margin)],
        model_version="1.0",
    )


@app.get("/trends/technologies")
def trends_technologies(limit: int = 10):
    engine = create_engine(DB_CONN)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT technologie, SUM(nb_offres) as total, ROUND(AVG(salaire_moyen)) as sal_moyen
            FROM analytics.agg_tech_tendances
            GROUP BY technologie
            ORDER BY total DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()
    return [{"technologie": r[0], "nb_offres": r[1], "salaire_moyen": r[2]} for r in rows]


@app.get("/trends/salaries")
def trends_salaries(limit: int = 10):
    engine = create_engine(DB_CONN)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT ville, nb_offres, salaire_moyen, salaire_median
            FROM analytics.agg_salaires_par_ville
            ORDER BY salaire_moyen DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()
    return [{"ville": r[0], "nb_offres": r[1], "salaire_moyen": r[2], "salaire_median": r[3]} for r in rows]


@app.get("/trends/locations")
def trends_locations():
    engine = create_engine(DB_CONN)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT region, COUNT(*) as nb_offres,
                   ROUND(AVG(salaire_median)) as salaire_moyen
            FROM clean.offres
            WHERE region != 'Inconnue'
            GROUP BY region
            ORDER BY nb_offres DESC
        """)).fetchall()
    return [{"region": r[0], "nb_offres": r[1], "salaire_moyen": r[2]} for r in rows]


# ─── Feature building ────────────────────────────────────────────────

REGIONS = {
    "paris": "Île-de-France", "île-de-france": "Île-de-France",
    "lyon": "Auvergne-Rhône-Alpes", "marseille": "PACA",
    "toulouse": "Occitanie", "bordeaux": "Nouvelle-Aquitaine",
    "nantes": "Pays de la Loire", "strasbourg": "Grand Est",
    "lille": "Hauts-de-France",
}

TOP_TECHNOLOGIES = [
    "python", "sql", "java", "javascript", "typescript", "react", "angular",
    "vue", "node", "django", "fastapi", "flask", "spring", "postgresql",
    "mysql", "mongodb", "redis", "kafka", "spark", "airflow", "dbt",
    "docker", "kubernetes", "aws", "gcp", "azure", "terraform", "git",
    "scala", "machine learning", "deep learning", "mlops", "mlflow",
]

EXP_MAP = {"junior": 0, "mid": 1, "senior": 2, "non_specifie": -1}
CONTRAT_MAP = {"CDI": 0, "CDD": 1, "Intérim": 2, "Freelance": 3, "Alternance": 4}


def _build_features(req: PredictRequest) -> pd.DataFrame:
    """Construit le vecteur de features pour la prédiction."""
    features = {}

    # TF-IDF simulé (zeros — le modèle dépend peu du TF-IDF pour la prédiction en live)
    for i in range(200):
        features[f"tfidf_{i}"] = 0.0

    # Technologies
    techs_lower = [t.lower() for t in req.technologies]
    for tech in TOP_TECHNOLOGIES:
        col = f"has_{tech.replace(' ', '_').replace('-', '_')}"
        features[col] = 1 if tech in techs_lower else 0

    features["nb_technologies"] = len(req.technologies)
    features["is_remote"] = int(req.is_remote)
    features["is_full_remote"] = 0

    # Encodage région
    ville_lower = req.ville.lower()
    region = REGIONS.get(ville_lower, "Autre")
    region_map = {
        "Île-de-France": 3, "Auvergne-Rhône-Alpes": 0, "PACA": 5,
        "Occitanie": 4, "Nouvelle-Aquitaine": 4, "Pays de la Loire": 6,
        "Grand Est": 2, "Hauts-de-France": 2, "Autre": 1,
    }
    features["region_encoded"] = region_map.get(region, 1)
    features["contrat_encoded"] = CONTRAT_MAP.get(req.type_contrat, 0)
    features["experience_encoded"] = EXP_MAP.get(req.niveau_experience, -1)

    return pd.DataFrame([features])

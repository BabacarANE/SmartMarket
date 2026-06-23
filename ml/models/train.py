"""
Entraînement des modèles ML — SmartMarket Intelligence
Baseline + XGBoost + LightGBM avec tracking MLflow
"""

from __future__ import annotations

import logging
import os

import mlflow
import mlflow.sklearn
import mlflow.xgboost
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

logger = logging.getLogger(__name__)

MLFLOW_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
EXPERIMENT_NAME = "smartmarket-salary-prediction"

# Features à utiliser pour l'entraînement
FEATURE_COLS = (
    [f"tfidf_{i}" for i in range(200)]
    + [
        "nb_technologies", "is_remote", "is_full_remote",
        "region_encoded", "contrat_encoded", "experience_encoded",
    ]
    + [
        f"has_{tech.replace(' ', '_').replace('-', '_')}"
        for tech in [
            "python", "sql", "java", "javascript", "typescript", "react",
            "angular", "vue", "node", "django", "fastapi", "flask", "spring",
            "postgresql", "mysql", "mongodb", "redis", "kafka", "spark",
            "airflow", "dbt", "docker", "kubernetes", "aws", "gcp", "azure",
            "terraform", "git", "scala", "machine learning", "deep learning",
            "mlops", "mlflow",
        ]
    ]
)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Calcule MAE, RMSE, R², MAPE."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    mape = np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1))) * 100
    return {"mae": mae, "rmse": rmse, "r2": r2, "mape": mape}


def prepare_data(df: pd.DataFrame):
    """Prépare X, y en filtrant les valeurs aberrantes."""
    # Filtre salaires aberrants
    df = df[
        (df["target_salaire"] >= 15000) &
        (df["target_salaire"] <= 200000)
    ].copy()

    # Garde uniquement les colonnes features disponibles
    available_cols = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available_cols].fillna(0)
    y = df["target_salaire"]

    return train_test_split(X, y, test_size=0.2, random_state=42)


def train_baseline(X_train, X_test, y_train, y_test) -> dict:
    """Baseline : médiane globale."""
    median_salary = y_train.median()
    y_pred = np.full(len(y_test), median_salary)
    metrics = compute_metrics(y_test.values, y_pred)
    logger.info(f"Baseline MAE: {metrics['mae']:.0f}€")
    return metrics


def train_model(
    model_name: str,
    model,
    X_train, X_test, y_train, y_test,
    params: dict,
) -> str:
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    exp = mlflow.get_experiment_by_name(EXPERIMENT_NAME)

    logger.info("Tracking URI : %s", mlflow.get_tracking_uri())

    if exp:
        logger.info(
            "Experiment ID=%s artifact_location=%s",
            exp.experiment_id,
            exp.artifact_location,
        )

    with mlflow.start_run(run_name=model_name) as run:
        mlflow.log_params(params)
        mlflow.log_param("train_size", len(X_train))
        mlflow.log_param("test_size", len(X_test))
        mlflow.log_param("n_features", X_train.shape[1])

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        metrics = compute_metrics(y_test.values, y_pred)
        mlflow.log_metrics({
            f"test_{k}": v for k, v in metrics.items()
        })

        # Baseline pour comparaison
        baseline = train_baseline(X_train, X_test, y_train, y_test)
        mlflow.log_metrics({
            f"baseline_{k}": v for k, v in baseline.items()
        })

        # Log du modèle via joblib + log_artifact sur le bon store
        import joblib, tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            model_path = os.path.join(tmp, "model.joblib")
            joblib.dump(model, model_path)
            mlflow.log_artifact(model_path)

        logger.info(
            f"{model_name} — MAE: {metrics['mae']:.0f}€  "
            f"R²: {metrics['r2']:.3f}  MAPE: {metrics['mape']:.1f}%"
        )

        return run.info.run_id


def run_training(db_conn_string: str) -> dict:
    """Lance l'entraînement complet."""
    from ml.features.engineer import FeatureEngineer

    logger.info("Construction des features...")
    fe = FeatureEngineer(db_conn_string)
    df = fe.build()

    X_train, X_test, y_train, y_test = prepare_data(df)
    logger.info(f"Train: {len(X_train)} | Test: {len(X_test)}")

    results = {}

    # XGBoost
    xgb_params = {
        "n_estimators": 200,
        "learning_rate": 0.1,
        "max_depth": 6,
        "random_state": 42,
    }
    run_id = train_model(
        "XGBoost",
        XGBRegressor(**xgb_params, verbosity=0),
        X_train, X_test, y_train, y_test,
        xgb_params,
    )
    results["xgboost_run_id"] = run_id

    # LightGBM
    lgbm_params = {
        "n_estimators": 200,
        "learning_rate": 0.1,
        "num_leaves": 31,
        "random_state": 42,
    }
    run_id = train_model(
        "LightGBM",
        LGBMRegressor(**lgbm_params, verbose=-1),
        X_train, X_test, y_train, y_test,
        lgbm_params,
    )
    results["lgbm_run_id"] = run_id

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    DB = "postgresql+pg8000://smartmarket:x@localhost:5433/smartmarket_db"
    results = run_training(DB)
    print(f"\nRuns MLflow : {results}")
    print(f"UI MLflow   : http://localhost:5000/#/experiments")

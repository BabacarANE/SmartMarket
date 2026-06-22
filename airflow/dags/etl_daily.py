"""
DAG ETL quotidien — SmartMarket Intelligence
Collecte → Nettoyage → dbt → Validation
Déclenchement : tous les jours à 06h00
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# Ajouter le path pour importer nos modules
sys.path.insert(0, "/opt/airflow")

logger = logging.getLogger(__name__)

DB_CONN = os.environ.get(
    "DB_CONN_STRING",
    "postgresql+pg8000://smartmarket:x@postgres:5432/smartmarket_db"
)

default_args = {
    "owner": "smartmarket",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "on_failure_callback": None,
}


def collect_france_travail(**context):
    """Collecte les offres depuis l'API France Travail."""
    from ml.collectors.france_travail import FranceTravailCollector

    collector = FranceTravailCollector(DB_CONN)
    report = collector.run()

    logger.info(str(report))

    if report.status == "failed":
        raise Exception(f"Collecte France Travail échouée: {report.error_message}")

    context["task_instance"].xcom_push(key="ft_inserted", value=report.nb_inserted)
    return report.nb_inserted


def collect_adzuna(**context):
    """Collecte les offres depuis l'API Adzuna."""
    from ml.collectors.adzuna import AdzunaCollector

    collector = AdzunaCollector(DB_CONN)
    report = collector.run()

    logger.info(str(report))

    if report.status == "failed":
        raise Exception(f"Collecte Adzuna échouée: {report.error_message}")

    context["task_instance"].xcom_push(key="adzuna_inserted", value=report.nb_inserted)
    return report.nb_inserted


def clean_and_deduplicate(**context):
    """Nettoie et normalise les données brutes."""
    from ml.collectors.cleaner import DataCleaner

    cleaner = DataCleaner(DB_CONN)
    result = cleaner.run()

    logger.info(f"Nettoyage terminé: {result}")

    if result["inserted"] == 0:
        logger.warning("Aucune nouvelle offre insérée dans clean.offres")

    return result["inserted"]


def validate_data_quality(**context):
    """Valide la qualité des données après le pipeline."""
    from sqlalchemy import create_engine, text

    engine = create_engine(DB_CONN)

    with engine.connect() as conn:
        # Vérification fraîcheur
        result = conn.execute(text("""
            SELECT COUNT(*) FROM raw.offres_emploi
            WHERE date_collecte >= NOW() - INTERVAL '25 hours'
        """)).fetchone()

        nb_recent = result[0]
        logger.info(f"Offres collectées dans les dernières 25h: {nb_recent}")

        if nb_recent == 0:
            raise Exception("Aucune offre récente trouvée — pipeline suspect")

        # Vérification taux salaires
        result = conn.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(salaire_min) as avec_salaire,
                ROUND(COUNT(salaire_min)::numeric / COUNT(*) * 100, 1) as pct
            FROM raw.offres_emploi
        """)).fetchone()

        logger.info(f"Total: {result[0]}, Avec salaire: {result[1]} ({result[2]}%)")

        if result[2] < 10:
            raise Exception(f"Taux de salaires trop bas: {result[2]}%")

    return {"nb_recent": nb_recent, "pct_salaire": float(result[2])}


with DAG(
    dag_id="etl_daily_pipeline",
    description="Pipeline ETL quotidien SmartMarket",
    schedule="0 6 * * *",
    start_date=datetime(2026, 6, 1),
    catchup=False,
    default_args=default_args,
    tags=["etl", "collecte", "smartmarket"],
    max_active_runs=1,
) as dag:

    t1_france_travail = PythonOperator(
        task_id="collect_france_travail",
        python_callable=collect_france_travail,
    )

    t2_adzuna = PythonOperator(
        task_id="collect_adzuna",
        python_callable=collect_adzuna,
    )

    t3_clean = PythonOperator(
        task_id="clean_and_deduplicate",
        python_callable=clean_and_deduplicate,
    )

    t4_dbt = BashOperator(
        task_id="run_dbt_models",
        bash_command="""
            cd /opt/airflow && \
            pip install dbt-core dbt-postgres -q && \
            dbt run --profiles-dir /opt/airflow/dbt --project-dir /opt/airflow \
            --target prod 2>&1 || true
        """,
    )

    t5_validate = PythonOperator(
        task_id="validate_data_quality",
        python_callable=validate_data_quality,
    )

    # Dépendances
    [t1_france_travail, t2_adzuna] >> t3_clean >> t4_dbt >> t5_validate

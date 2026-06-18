"""
Module de collecte de base — SmartMarket Intelligence
Toutes les sources héritent de BaseCollector.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import psycopg2
from psycopg2.extras import execute_values
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@dataclass
class CollectionReport:
    """Rapport résumant le résultat d'une collecte."""

    source: str
    run_date: datetime = field(default_factory=datetime.utcnow)
    nb_fetched: int = 0
    nb_inserted: int = 0
    nb_duplicates: int = 0
    nb_errors: int = 0
    status: str = "success"  # success | partial | failed
    error_message: str | None = None

    def __str__(self) -> str:
        return (
            f"[{self.source}] {self.status.upper()} — "
            f"fetched={self.nb_fetched}, inserted={self.nb_inserted}, "
            f"duplicates={self.nb_duplicates}, errors={self.nb_errors}"
        )


class BaseCollector(ABC):
    """
    Classe de base pour tous les collecteurs d'offres d'emploi.

    Chaque sous-classe implémente `fetch()` pour appeler sa source
    et mapper les résultats vers le schéma commun.
    """

    source_name: str = "unknown"

    def __init__(self, db_conn_string: str) -> None:
        self.db_conn_string = db_conn_string
        self.logger = logging.getLogger(self.__class__.__name__)

    # ─── Interface publique ──────────────────────────────────────────

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        """
        Appel l'API / scraping de la source.
        Retourne une liste de dicts mappés vers le schéma raw.offres_emploi.
        """
        ...

    def run(self) -> CollectionReport:
        """
        Point d'entrée principal : fetch → deduplicate → save.
        Retourne un CollectionReport.
        """
        report = CollectionReport(source=self.source_name)

        try:
            self.logger.info(f"Démarrage collecte — source={self.source_name}")
            raw_records = self.fetch()
            report.nb_fetched = len(raw_records)
            self.logger.info(f"{report.nb_fetched} offres récupérées")

            unique_records, duplicates_count = self.deduplicate(raw_records)
            report.nb_duplicates = duplicates_count
            self.logger.info(
                f"{duplicates_count} doublons ignorés, "
                f"{len(unique_records)} offres à insérer"
            )

            inserted = self.save_raw(unique_records)
            report.nb_inserted = inserted

        except Exception as exc:
            report.status = "failed"
            report.error_message = str(exc)
            report.nb_errors += 1
            self.logger.error(f"Échec collecte {self.source_name}: {exc}", exc_info=True)
        finally:
            self._log_report(report)

        self.logger.info(str(report))
        return report

    # ─── Déduplication ───────────────────────────────────────────────

    def deduplicate(
        self, records: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Déduplique en mémoire sur (source_id) avant d'insérer.
        La contrainte UNIQUE en base gère la déduplication inter-runs.
        """
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []

        for record in records:
            key = record.get("source_id", "")
            if key and key not in seen:
                seen.add(key)
                unique.append(record)

        duplicates = len(records) - len(unique)
        return unique, duplicates

    # ─── Persistance ─────────────────────────────────────────────────

    def save_raw(self, records: list[dict[str, Any]]) -> int:
        """
        Insère les offres dans raw.offres_emploi.
        Ignore silencieusement les conflits (ON CONFLICT DO NOTHING).
        Retourne le nombre d'offres effectivement insérées.
        """
        if not records:
            self.logger.info("Aucune offre à insérer")
            return 0

        columns = [
            "source", "source_id", "titre", "description", "entreprise",
            "ville", "departement", "type_contrat", "salaire_min", "salaire_max",
            "experience_requise", "technologies_raw", "date_publication",
        ]

        values = [
            tuple(record.get(col) for col in columns)
            for record in records
        ]

        sql = f"""
            INSERT INTO raw.offres_emploi
                ({', '.join(columns)})
            VALUES %s
            ON CONFLICT (source, source_id) DO NOTHING
        """

        try:
            with psycopg2.connect(self.db_conn_string) as conn:
                with conn.cursor() as cur:
                    execute_values(cur, sql, values)
                    inserted = cur.rowcount
                    conn.commit()
            self.logger.info(f"{inserted} offres insérées en base")
            return inserted
        except Exception as exc:
            self.logger.error(f"Erreur insertion PostgreSQL: {exc}", exc_info=True)
            raise

    # ─── Logging du rapport ──────────────────────────────────────────

    def _log_report(self, report: CollectionReport) -> None:
        """Persiste le rapport de collecte dans raw.collection_logs."""
        sql = """
            INSERT INTO raw.collection_logs
                (source, run_date, nb_fetched, nb_inserted, nb_duplicates,
                 nb_errors, status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            with psycopg2.connect(self.db_conn_string) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (
                        report.source,
                        report.run_date,
                        report.nb_fetched,
                        report.nb_inserted,
                        report.nb_duplicates,
                        report.nb_errors,
                        report.status,
                        report.error_message,
                    ))
                    conn.commit()
        except Exception as exc:
            # On ne lève pas ici — on ne veut pas masquer l'erreur principale
            self.logger.warning(f"Impossible de logger le rapport: {exc}")

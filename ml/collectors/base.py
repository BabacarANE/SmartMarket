"""
Module de collecte de base — SmartMarket Intelligence
Utilise SQLAlchemy + pg8000.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


def _make_engine(db_conn_string: str):
    """Crée un engine SQLAlchemy en forçant pg8000 si besoin."""
    if "postgresql" in db_conn_string and "+pg8000" not in db_conn_string:
        db_conn_string = db_conn_string.replace("postgresql://", "postgresql+pg8000://")
    return create_engine(db_conn_string)


@dataclass
class CollectionReport:
    source: str
    run_date: datetime = field(default_factory=datetime.utcnow)
    nb_fetched: int = 0
    nb_inserted: int = 0
    nb_duplicates: int = 0
    nb_errors: int = 0
    status: str = "success"
    error_message: str | None = None

    def __str__(self) -> str:
        return (
            f"[{self.source}] {self.status.upper()} — "
            f"fetched={self.nb_fetched}, inserted={self.nb_inserted}, "
            f"duplicates={self.nb_duplicates}, errors={self.nb_errors}"
        )


class BaseCollector(ABC):
    source_name: str = "unknown"

    def __init__(self, db_conn_string: str) -> None:
        self.db_conn_string = db_conn_string
        self.engine = _make_engine(db_conn_string)
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]: ...

    def run(self) -> CollectionReport:
        report = CollectionReport(source=self.source_name)
        try:
            self.logger.info(f"Démarrage collecte — source={self.source_name}")
            raw_records = self.fetch()
            report.nb_fetched = len(raw_records)
            unique_records, duplicates_count = self.deduplicate(raw_records)
            report.nb_duplicates = duplicates_count
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

    def deduplicate(self, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for record in records:
            key = record.get("source_id", "")
            if key and key not in seen:
                seen.add(key)
                unique.append(record)
        return unique, len(records) - len(unique)

    def save_raw(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0

        columns = [
            "source", "source_id", "titre", "description", "entreprise",
            "ville", "departement", "type_contrat", "salaire_min",
            "salaire_max", "experience_requise", "technologies_raw",
            "date_publication",
        ]

        sql = text(f"""
            INSERT INTO raw.offres_emploi ({', '.join(columns)})
            VALUES ({', '.join([':' + c for c in columns])})
            ON CONFLICT (source, source_id) DO NOTHING
        """)

        rows = [
            {col: (str(record.get(col)) if isinstance(record.get(col), list) else record.get(col))
             for col in columns}
            for record in records
        ]

        try:
            with self.engine.begin() as conn:
                result = conn.execute(sql, rows)
                inserted = result.rowcount or 0
            self.logger.info(f"{inserted} offres insérées en base")
            return inserted
        except Exception as exc:
            self.logger.error(f"Erreur insertion PostgreSQL: {exc}", exc_info=True)
            raise

    def _log_report(self, report: CollectionReport) -> None:
        sql = text("""
            INSERT INTO raw.collection_logs
            (source, run_date, nb_fetched, nb_inserted, nb_duplicates,
             nb_errors, status, error_message)
            VALUES (:source, :run_date, :nb_fetched, :nb_inserted,
                    :nb_duplicates, :nb_errors, :status, :error_message)
        """)
        try:
            with self.engine.begin() as conn:
                conn.execute(sql, {
                    "source": report.source,
                    "run_date": report.run_date,
                    "nb_fetched": report.nb_fetched,
                    "nb_inserted": report.nb_inserted,
                    "nb_duplicates": report.nb_duplicates,
                    "nb_errors": report.nb_errors,
                    "status": report.status,
                    "error_message": report.error_message,
                })
        except Exception as exc:
            self.logger.warning(f"Impossible de logger le rapport: {exc}")

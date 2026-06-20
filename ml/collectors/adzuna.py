"""
Collecteur API Adzuna
Documentation : https://developer.adzuna.com
Auth : API key (app_id + api_key)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)

from ml.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

BASE_URL = "https://api.adzuna.com/v1/api/jobs/fr/search"
PAGE_SIZE = 50  # max Adzuna
MAX_PAGES = 20  # 1000 offres max par run

# Mots-clés tech pour filtrer les offres
TECH_KEYWORDS = [
    "data engineer", "data scientist", "machine learning", "devops",
    "développeur python", "backend developer", "fullstack", "cloud engineer",
    "mlops", "software engineer", "développeur java", "développeur react",
]


class AdzunaCollector(BaseCollector):
    """
    Collecte les offres d'emploi tech depuis l'API Adzuna (France).
    Parcourt plusieurs mots-clés tech et gère la pagination.
    """

    source_name = "adzuna"

    def __init__(self, db_conn_string: str) -> None:
        super().__init__(db_conn_string)
        self.app_id = os.environ["ADZUNA_APP_ID"]
        self.api_key = os.environ["ADZUNA_API_KEY"]

    # ─── Fetch ───────────────────────────────────────────────────────

    def fetch(self) -> list[dict[str, Any]]:
        """Collecte les offres tech récentes depuis Adzuna."""
        all_records: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for keyword in TECH_KEYWORDS:
            self.logger.info(f"Collecte Adzuna — keyword='{keyword}'")
            records = self._fetch_for_keyword(keyword)

            # Déduplication inter-keywords
            new_records = [r for r in records if r["source_id"] not in seen_ids]
            seen_ids.update(r["source_id"] for r in new_records)
            all_records.extend(new_records)

            self.logger.info(f"  → {len(new_records)} nouvelles offres")

        return all_records

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_for_keyword(
        self, keyword: str
    ) -> list[dict[str, Any]]:
        """Pagine sur les résultats Adzuna pour un keyword donné."""
        records: list[dict[str, Any]] = []

        for page in range(1, MAX_PAGES + 1):
            params = {
                "app_id": self.app_id,
                "app_key": self.api_key,
                "results_per_page": PAGE_SIZE,
                "page": page,
                "what": keyword,
                "where": "france",
                "sort_by": "date",
                "max_days_old": 3,
            }

            resp = requests.get(
                f"{BASE_URL}/{page}",  # ← page dans le chemin
                params={
                    "app_id": self.app_id,
                    "app_key": self.api_key,
                    "results_per_page": PAGE_SIZE,
                    "what": keyword,
                    "where": "france",
                    "sort_by": "date",
                    "max_days_old": 3,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            jobs = data.get("results", [])
            if not jobs:
                break

            for job in jobs:
                mapped = self._map_job(job)
                if mapped:
                    records.append(mapped)

            # Vérifier si on a tout récupéré
            total = data.get("count", 0)
            if page * PAGE_SIZE >= total:
                break

        return records

    # ─── Mapping ─────────────────────────────────────────────────────

    def _map_job(self, job: dict[str, Any]) -> dict[str, Any] | None:
        """Mappe une offre Adzuna vers le schéma raw."""
        try:
            salary_min = self._to_annual(job.get("salary_min"))
            salary_max = self._to_annual(job.get("salary_max"))

            # Extraction département depuis le code postal
            location = job.get("location", {})
            area = location.get("area", [])
            ville = area[-1] if area else location.get("display_name", "")

            return {
                "source": self.source_name,
                "source_id": str(job.get("id", "")),
                "titre": job.get("title", "")[:500],
                "description": job.get("description", ""),
                "entreprise": job.get("company", {}).get("display_name", ""),
                "ville": ville,
                "departement": None,  # Non fourni par Adzuna
                "type_contrat": job.get("contract_type", ""),
                "salaire_min": salary_min,
                "salaire_max": salary_max,
                "experience_requise": job.get("contract_time", ""),
                "technologies_raw": job.get("category", {}).get("label", ""),
                "date_publication": job.get("created", "")[:10] or None,
            }
        except Exception as exc:
            self.logger.warning(f"Erreur mapping job {job.get('id')}: {exc}")
            return None

    @staticmethod
    def _to_annual(value: float | None) -> int | None:
        """
        Adzuna retourne parfois des salaires mensuels.
        On ne convertit pas ici — on garde tel quel s'il semble annuel (>= 15000).
        """
        if value is None:
            return None
        val = int(value)
        # Heuristique : si < 5000, c'est probablement mensuel → annualiser
        if val < 5000:
            return val * 12
        return val

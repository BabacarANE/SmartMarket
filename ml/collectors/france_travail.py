"""
Collecteur API France Travail (ex Pôle Emploi)
Documentation : https://francetravail.io/data/api
Auth : OAuth2 client_credentials
"""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta
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

# ─── Constantes ──────────────────────────────────────────────────────

AUTH_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
SCOPE = "api_offresdemploiv2 o2dsoffre"

# Codes ROME pour les métiers tech
ROME_TECH_CODES = [
    "M1805",  # Études et développement informatique
    "M1806",  # Conseil et maîtrise d'ouvrage systèmes d'information
    "M1810",  # Production et exploitation de systèmes d'information
    "M1811",  # Data / IA
    "M1812",  # Sécurité des systèmes d'information
]

PAGE_SIZE = 150  # max autorisé par l'API


class FranceTravailCollector(BaseCollector):
    """
    Collecte les offres d'emploi tech depuis l'API France Travail.
    Gère l'authentification OAuth2, la pagination et le mapping des champs.
    """

    source_name = "france_travail"

    def __init__(self, db_conn_string: str) -> None:
        super().__init__(db_conn_string)
        self.client_id = os.environ["FRANCE_TRAVAIL_CLIENT_ID"]
        self.client_secret = os.environ["FRANCE_TRAVAIL_CLIENT_SECRET"]
        self._access_token: str | None = None

    # ─── OAuth2 ──────────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _get_access_token(self) -> str:
        """Obtient un token OAuth2 via client_credentials."""
        resp = requests.post(
            AUTH_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=(
                f"grant_type=client_credentials"
                f"&client_id={self.client_id}"
                f"&client_secret={self.client_secret}"
                f"&scope=api_offresdemploiv2%20o2dsoffre"
            ),
            timeout=10,
        )
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]
        self.logger.info("Token OAuth2 obtenu")
        return self._access_token
    # ─── Fetch ───────────────────────────────────────────────────────

    def fetch(self) -> list[dict[str, Any]]:
        token = self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        all_records: list[dict[str, Any]] = []

        for rome_code in ROME_TECH_CODES:
            self.logger.info(f"Collecte ROME {rome_code}...")
            records = self._fetch_paginated(headers, rome_code, "")
            all_records.extend(records)
            self.logger.info(f"  → {len(records)} offres")

        return all_records

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _fetch_paginated(
            self,
            headers: dict[str, str],
            rome_code: str,
            date_min: str,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        start = 0

        while True:
            params = {
                "codeROME": rome_code,
                "range": f"{start}-{start + PAGE_SIZE - 1}",
                "sort": "1",
            }

            resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=15)

            if resp.status_code == 204:
                break
            resp.raise_for_status()

            data = resp.json()
            offres = data.get("resultats", [])

            if not offres:
                break

            for offre in offres:
                mapped = self._map_offre(offre)
                if mapped:
                    records.append(mapped)

            content_range = resp.headers.get("Content-Range", "")
            if content_range:
                try:
                    total = int(content_range.split("/")[-1])
                    if start + PAGE_SIZE >= total:
                        break
                except ValueError:
                    break

            start += PAGE_SIZE

        return records

    # ─── Mapping ─────────────────────────────────────────────────────

    def _map_offre(self, offre: dict[str, Any]) -> dict[str, Any] | None:
        """Mappe une offre API France Travail vers le schéma raw."""
        try:
            salaire_raw = offre.get("salaire", {})
            salaire_min, salaire_max = self._parse_salaire(salaire_raw)

            return {
                "source": self.source_name,
                "source_id": offre.get("id", ""),
                "titre": offre.get("intitule", "")[:500],
                "description": offre.get("description", ""),
                "entreprise": offre.get("entreprise", {}).get("nom", ""),
                "ville": offre.get("lieuTravail", {}).get("libelle", ""),
                "departement": offre.get("lieuTravail", {}).get("codePostal", "")[:10],
                "type_contrat": offre.get("typeContratLibelle", ""),
                "salaire_min": salaire_min,
                "salaire_max": salaire_max,
                "experience_requise": offre.get("experienceLibelle", ""),
                "technologies_raw": offre.get("competences", []),
                "date_publication": offre.get("dateCreation", "")[:10] or None,
            }
        except Exception as exc:
            self.logger.warning(f"Erreur mapping offre {offre.get('id')}: {exc}")
            return None

    @staticmethod
    def _parse_salaire(salaire_raw: dict) -> tuple[int | None, int | None]:
        if not salaire_raw:
            return None, None

        libelle = salaire_raw.get("libelle", "")
        if not libelle:
            return None, None

        import re
        # Extrait tous les nombres >= 4 chiffres
        numbers = re.findall(r"\d+(?:\.\d+)?", libelle)
        numbers = [float(n) for n in numbers if float(n) >= 1000]

        if not numbers:
            return None, None

        sal_min = int(min(numbers))
        sal_max = int(max(numbers))

        # Détecte si c'est mensuel → annualise
        if "mensuel" in libelle.lower() or "mois" in libelle.lower():
            # Vérifie que c'est bien un salaire mensuel (< 15000)
            if sal_min < 15000:
                sal_min = sal_min * 12
                sal_max = sal_max * 12

        return sal_min, sal_max

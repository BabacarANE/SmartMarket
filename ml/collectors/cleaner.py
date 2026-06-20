"""
Module de nettoyage et normalisation des offres brutes.
Prépare les données du schéma raw vers clean.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# ─── Mappings de normalisation ────────────────────────────────────────

CONTRAT_MAP = {
    "cdi": "CDI", "contrat à durée indéterminée": "CDI",
    "cdd": "CDD", "contrat à durée déterminée": "CDD",
    "mis": "Intérim", "intérim": "Intérim", "interim": "Intérim",
    "freelance": "Freelance", "indépendant": "Freelance",
    "alternance": "Alternance", "apprentissage": "Alternance",
    "stage": "Stage",
    "permanent": "CDI", "contract": "CDD", "temporary": "Intérim",
}

EXPERIENCE_MAP = {
    "débutant": "junior", "débutant accepté": "junior",
    "d": "junior", "0": "junior",
    "1 an": "junior", "2 an": "junior", "2 an(s)": "junior",
    "confirmé": "mid", "3 an": "mid", "3 an(s)": "mid",
    "4 an": "mid", "4 an(s)": "mid", "48 mois": "mid",
    "senior": "senior", "5 an": "senior", "5 an(s)": "senior",
    "e": "mid",  # "Exigé" sans précision → mid par défaut
}

TECH_KEYWORDS = [
    "python", "java", "javascript", "typescript", "react", "angular", "vue",
    "node", "django", "fastapi", "flask", "spring", "sql", "postgresql",
    "mysql", "mongodb", "redis", "elasticsearch", "kafka", "spark", "airflow",
    "dbt", "docker", "kubernetes", "aws", "gcp", "azure", "terraform",
    "git", "linux", "bash", "scala", "rust", "go", "php", "ruby", "swift",
    "machine learning", "deep learning", "nlp", "mlops", "mlflow",
    "scikit-learn", "tensorflow", "pytorch", "pandas", "numpy",
    "tableau", "power bi", "looker", "dbt", "snowflake", "databricks",
]

REMOTE_KEYWORDS = ["télétravail", "remote", "full remote", "distanciel", "hybride"]
FULL_REMOTE_KEYWORDS = ["full remote", "100% télétravail", "100% remote", "full distanciel"]


class DataCleaner:
    """
    Nettoie et normalise les données brutes vers le schéma clean.
    """

    def __init__(self, db_conn_string: str) -> None:
        self.engine = create_engine(db_conn_string)
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self) -> dict[str, int]:
        """Pipeline complet : load → clean → save."""
        self.logger.info("Démarrage nettoyage...")

        df = self._load_raw()
        self.logger.info(f"{len(df)} offres brutes chargées")

        df = self._clean(df)
        self.logger.info(f"{len(df)} offres après nettoyage")

        inserted = self._save_clean(df)
        self.logger.info(f"{inserted} offres insérées dans clean.offres")

        return {"loaded": len(df), "inserted": inserted}

    # ─── Load ────────────────────────────────────────────────────────

    def _load_raw(self) -> pd.DataFrame:
        """Charge les offres brutes non encore nettoyées."""
        sql = """
            SELECT r.*
            FROM raw.offres_emploi r
            LEFT JOIN clean.offres c ON r.id = c.raw_id
            WHERE c.raw_id IS NULL
        """
        with self.engine.connect() as conn:
            return pd.read_sql(sql, conn)

    # ─── Clean ───────────────────────────────────────────────────────

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Texte
        df["titre"] = df["titre"].apply(self._clean_text)
        df["entreprise"] = df["entreprise"].apply(self._clean_text)
        df["ville"] = df["ville"].apply(self._normalize_ville)

        # Normalisation des catégories
        df["type_contrat"] = df["type_contrat"].apply(self._normalize_contrat)
        df["niveau_experience"] = df["experience_requise"].apply(self._normalize_experience)

        # Salaire médian
        df["salaire_median"] = df.apply(
            lambda r: int((r["salaire_min"] + r["salaire_max"]) / 2)
            if pd.notna(r["salaire_min"]) and pd.notna(r["salaire_max"])
            else None,
            axis=1,
        )

        # Technologies parsées
        df["technologies"] = df.apply(
            lambda r: self._parse_technologies(r["description"], r["technologies_raw"]),
            axis=1,
        )

        # Remote
        df["is_remote"] = df["description"].apply(
            lambda d: any(kw in str(d).lower() for kw in REMOTE_KEYWORDS)
        )
        df["is_full_remote"] = df["description"].apply(
            lambda d: any(kw in str(d).lower() for kw in FULL_REMOTE_KEYWORDS)
        )

        # Région
        df["region"] = df["departement"].apply(self._departement_to_region)

        # Supprimer les offres sans titre
        df = df[df["titre"].str.len() > 2]

        return df

    # ─── Normalisation ───────────────────────────────────────────────

    @staticmethod
    def _clean_text(text: Any) -> str:
        if not text or pd.isna(text):
            return ""
        text = str(text).strip()
        text = re.sub(r"\s+", " ", text)
        return text[:500]

    @staticmethod
    def _normalize_ville(ville: Any) -> str:
        if not ville or pd.isna(ville):
            return ""
        ville = str(ville).strip()
        # Retire les codes postaux "75 - Paris" → "Paris"
        ville = re.sub(r"^\d+\s*[-–]\s*", "", ville)
        return ville.strip().title()[:100]

    @staticmethod
    def _normalize_contrat(contrat: Any) -> str:
        if not contrat or pd.isna(contrat):
            return "Autre"
        key = str(contrat).lower().strip()
        for pattern, normalized in CONTRAT_MAP.items():
            if pattern in key:
                return normalized
        return str(contrat).strip()[:20] or "Autre"

    @staticmethod
    def _normalize_experience(exp: Any) -> str:
        if not exp or pd.isna(exp):
            return "non_specifie"
        key = str(exp).lower().strip()
        for pattern, normalized in EXPERIENCE_MAP.items():
            if pattern in key:
                return normalized
        # Détection par nombre d'années
        match = re.search(r"(\d+)", key)
        if match:
            years = int(match.group(1))
            if years <= 2:
                return "junior"
            elif years <= 4:
                return "mid"
            else:
                return "senior"
        return "non_specifie"

    @staticmethod
    def _parse_technologies(description: Any, technologies_raw: Any) -> list[str]:
        """Extrait les technologies mentionnées dans la description."""
        text = f"{description or ''} {technologies_raw or ''}".lower()
        found = []
        for tech in TECH_KEYWORDS:
            if tech.lower() in text:
                found.append(tech)
        return found

    @staticmethod
    def _departement_to_region(dept: Any) -> str:
        if not dept or pd.isna(dept):
            return "Inconnue"
        dept_str = str(dept).strip()[:2]
        regions = {
            "75": "Île-de-France", "77": "Île-de-France", "78": "Île-de-France",
            "91": "Île-de-France", "92": "Île-de-France", "93": "Île-de-France",
            "94": "Île-de-France", "95": "Île-de-France",
            "13": "PACA", "06": "PACA", "83": "PACA", "84": "PACA",
            "69": "Auvergne-Rhône-Alpes", "38": "Auvergne-Rhône-Alpes",
            "74": "Auvergne-Rhône-Alpes", "01": "Auvergne-Rhône-Alpes",
            "31": "Occitanie", "34": "Occitanie", "33": "Nouvelle-Aquitaine",
            "44": "Pays de la Loire", "67": "Grand Est", "59": "Hauts-de-France",
            "76": "Normandie", "35": "Bretagne", "21": "Bourgogne-Franche-Comté",
        }
        return regions.get(dept_str, "Autre")

    # ─── Save ────────────────────────────────────────────────────────

    def _save_clean(self, df: pd.DataFrame) -> int:
        """Insère les offres nettoyées dans clean.offres."""
        columns = [
            "raw_id", "source", "source_id", "titre", "description",
            "entreprise", "ville", "departement", "type_contrat",
            "salaire_min", "salaire_max", "salaire_median",
            "niveau_experience", "technologies", "is_remote", "is_full_remote",
            "region", "date_publication", "date_collecte",
        ]

        df["raw_id"] = df["id"]
        df["technologies"] = df["technologies"].apply(
            lambda t: "{" + ",".join(t) + "}" if t else "{}"
        )

        sql = text(f"""
            INSERT INTO clean.offres ({', '.join(columns)})
            VALUES ({', '.join([':' + c for c in columns])})
            ON CONFLICT (source, source_id) DO NOTHING
        """)

        # Conversion explicite colonne par colonne APRÈS le where
        rows = []
        for _, row in df[columns].iterrows():
            record = {}
            for col in columns:
                val = row[col]
                if col in ["salaire_min", "salaire_max", "salaire_median"]:
                    record[col] = int(val) if val is not None and str(val) != 'nan' else None
                elif pd.isna(val) if not isinstance(val, (list, dict, str)) else False:
                    record[col] = None
                else:
                    record[col] = val
            rows.append(record)

        try:
            with self.engine.begin() as conn:
                result = conn.execute(sql, rows)
                return result.rowcount or 0
        except Exception as exc:
            self.logger.error(f"Erreur insertion clean: {exc}", exc_info=True)
            raise

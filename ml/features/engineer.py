"""
Feature Engineering — SmartMarket Intelligence
Construit le dataset ML à partir de clean.offres
"""

from __future__ import annotations

import logging
import re
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

TOP_TECHNOLOGIES = [
    "python", "sql", "java", "javascript", "typescript", "react", "angular",
    "vue", "node", "django", "fastapi", "flask", "spring", "postgresql",
    "mysql", "mongodb", "redis", "kafka", "spark", "airflow", "dbt",
    "docker", "kubernetes", "aws", "gcp", "azure", "terraform", "git",
    "scala", "machine learning", "deep learning", "mlops", "mlflow",
]


class FeatureEngineer:
    """
    Construit le feature set ML depuis clean.offres.
    Features : TF-IDF description, one-hot technologies,
               encodage région/contrat/expérience, indicateurs booléens.
    """

    def __init__(self, db_conn_string: str) -> None:
        self.engine = create_engine(db_conn_string)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tfidf = TfidfVectorizer(max_features=200, stop_words=None)
        self.region_encoder = LabelEncoder()
        self.contrat_encoder = LabelEncoder()
        self.exp_encoder = OrdinalEncoder(
            categories=[["junior", "mid", "senior", "non_specifie"]],
            handle_unknown="use_encoded_value",
            unknown_value=-1,
        )

    def build(self) -> pd.DataFrame:
        """Pipeline complet : load → features → retourne le DataFrame."""
        self.logger.info("Chargement des données...")
        df = self._load_data()
        self.logger.info(f"{len(df)} offres chargées")

        df = self._add_text_features(df)
        df = self._add_tech_features(df)
        df = self._add_categorical_features(df)
        df = self._add_boolean_features(df)

        # Garder uniquement les offres avec salaire pour l'entraînement
        df_with_salary = df[df["target_salaire"].notna()].copy()
        self.logger.info(
            f"Dataset ML : {len(df_with_salary)} offres avec salaire "
            f"/ {len(df)} total"
        )
        return df_with_salary

    def _load_data(self) -> pd.DataFrame:
        sql = """
            SELECT
                id,
                titre,
                description,
                ville,
                region,
                type_contrat,
                niveau_experience,
                technologies,
                is_remote,
                is_full_remote,
                salaire_median as target_salaire,
                date_publication
            FROM clean.offres
            WHERE titre IS NOT NULL
        """
        with self.engine.connect() as conn:
            return pd.read_sql(sql, conn)

    def _add_text_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """TF-IDF sur la description."""
        descriptions = df["description"].fillna("").astype(str)
        tfidf_matrix = self.tfidf.fit_transform(descriptions)

        tfidf_df = pd.DataFrame(
            tfidf_matrix.toarray(),
            columns=[f"tfidf_{i}" for i in range(tfidf_matrix.shape[1])],
            index=df.index,
        )
        return pd.concat([df, tfidf_df], axis=1)

    def _add_tech_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """One-hot encoding des technologies."""
        for tech in TOP_TECHNOLOGIES:
            col_name = f"has_{tech.replace(' ', '_').replace('-', '_')}"
            df[col_name] = df["technologies"].apply(
                lambda techs: 1 if isinstance(techs, list) and tech in techs else 0
            )
        df["nb_technologies"] = df["technologies"].apply(
            lambda t: len(t) if isinstance(t, list) else 0
        )
        return df

    def _add_categorical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Label encoding région, contrat, expérience."""
        df["region"] = df["region"].fillna("Inconnue")
        df["type_contrat"] = df["type_contrat"].fillna("Autre")
        df["niveau_experience"] = df["niveau_experience"].fillna("non_specifie")

        df["region_encoded"] = self.region_encoder.fit_transform(df["region"])
        df["contrat_encoded"] = self.contrat_encoder.fit_transform(df["type_contrat"])
        df["experience_encoded"] = self.exp_encoder.fit_transform(
            df[["niveau_experience"]]
        ).ravel()

        return df

    def _add_boolean_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Indicateurs booléens."""
        df["is_remote"] = df["is_remote"].fillna(False).astype(int)
        df["is_full_remote"] = df["is_full_remote"].fillna(False).astype(int)
        return df

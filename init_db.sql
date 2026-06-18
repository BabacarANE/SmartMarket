-- SmartMarket Intelligence — Initialisation de la base de données
-- Ce script est exécuté automatiquement au premier démarrage du container PostgreSQL

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Schémas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS clean;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS features;

-- ─────────────────────────────────────────────────────────────────────
-- SCHÉMA RAW — Données brutes telles que collectées
-- ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS raw.offres_emploi (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source              VARCHAR(50)  NOT NULL,   -- france_travail | adzuna | wtj
    source_id           VARCHAR(100) NOT NULL,
    titre               TEXT         NOT NULL,
    description         TEXT,
    entreprise          VARCHAR(255),
    ville               VARCHAR(100),
    departement         VARCHAR(10),
    type_contrat        VARCHAR(20),             -- CDI, CDD, freelance...
    salaire_min         INTEGER,                 -- €/an
    salaire_max         INTEGER,                 -- €/an
    experience_requise  VARCHAR(50),             -- Junior / Confirmé / Senior
    technologies_raw    TEXT,                    -- stack brute non parsée
    date_publication    DATE,
    date_collecte       TIMESTAMP    NOT NULL DEFAULT NOW(),
    est_actif           BOOLEAN      NOT NULL DEFAULT TRUE,
    -- Contrainte de déduplication
    UNIQUE (source, source_id)
);

-- Index utiles
CREATE INDEX IF NOT EXISTS idx_raw_offres_source        ON raw.offres_emploi(source);
CREATE INDEX IF NOT EXISTS idx_raw_offres_date_pub      ON raw.offres_emploi(date_publication);
CREATE INDEX IF NOT EXISTS idx_raw_offres_date_collecte ON raw.offres_emploi(date_collecte);
CREATE INDEX IF NOT EXISTS idx_raw_offres_ville         ON raw.offres_emploi(ville);

-- ─────────────────────────────────────────────────────────────────────
-- TABLE DE SUIVI DES COLLECTES (logs pipeline)
-- ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS raw.collection_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source          VARCHAR(50)  NOT NULL,
    run_date        TIMESTAMP    NOT NULL DEFAULT NOW(),
    nb_fetched      INTEGER      NOT NULL DEFAULT 0,
    nb_inserted     INTEGER      NOT NULL DEFAULT 0,
    nb_duplicates   INTEGER      NOT NULL DEFAULT 0,
    nb_errors       INTEGER      NOT NULL DEFAULT 0,
    status          VARCHAR(20)  NOT NULL DEFAULT 'success',  -- success | partial | failed
    error_message   TEXT
);

-- ─────────────────────────────────────────────────────────────────────
-- Grants (si besoin d'utilisateurs séparés en prod)
-- ─────────────────────────────────────────────────────────────────────

-- GRANT USAGE ON SCHEMA raw      TO smartmarket;
-- GRANT USAGE ON SCHEMA clean    TO smartmarket;
-- GRANT USAGE ON SCHEMA analytics TO smartmarket;
-- GRANT USAGE ON SCHEMA features  TO smartmarket;

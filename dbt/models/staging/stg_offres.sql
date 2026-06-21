-- Modèle staging : nettoyage et normalisation des offres brutes
-- Source : raw.offres_emploi → Vue dans clean

{{ config(materialized='view') }}

SELECT
    id                                          AS offre_id,
    source,
    source_id,
    TRIM(titre)                                 AS titre,
    TRIM(description)                           AS description,
    COALESCE(NULLIF(TRIM(entreprise), ''), 'Inconnue') AS entreprise,
    COALESCE(NULLIF(TRIM(ville), ''), 'Inconnue')      AS ville,
    NULLIF(TRIM(departement), '')               AS departement,
    COALESCE(NULLIF(TRIM(type_contrat), ''), 'Autre')  AS type_contrat,
    salaire_min,
    salaire_max,
    CASE
        WHEN salaire_min IS NOT NULL AND salaire_max IS NOT NULL
        THEN (salaire_min + salaire_max) / 2
        WHEN salaire_min IS NOT NULL THEN salaire_min
        WHEN salaire_max IS NOT NULL THEN salaire_max
        ELSE NULL
    END                                         AS salaire_median,
    LOWER(TRIM(experience_requise))             AS experience_requise,
    date_publication,
    date_collecte,
    est_actif
FROM raw.offres_emploi
WHERE titre IS NOT NULL
  AND TRIM(titre) != ''

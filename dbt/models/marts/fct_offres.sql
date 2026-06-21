{{ config(materialized='table', schema='analytics') }}

SELECT
    o.offre_id,
    o.source,
    o.titre,
    o.entreprise,
    o.ville,
    o.departement,
    o.type_contrat,
    o.salaire_min,
    o.salaire_max,
    o.salaire_median,
    o.experience_requise,
    o.date_publication,
    o.date_collecte,
    -- Features dérivées
    EXTRACT(YEAR FROM o.date_publication)   AS annee,
    EXTRACT(MONTH FROM o.date_publication)  AS mois,
    CASE WHEN o.salaire_median IS NOT NULL THEN TRUE ELSE FALSE END AS has_salaire,
    CASE
        WHEN o.salaire_median < 30000 THEN 'junior'
        WHEN o.salaire_median < 50000 THEN 'mid'
        WHEN o.salaire_median < 70000 THEN 'senior'
        ELSE 'expert'
    END AS tranche_salaire
FROM {{ ref('stg_offres') }} o
WHERE o.date_publication IS NOT NULL

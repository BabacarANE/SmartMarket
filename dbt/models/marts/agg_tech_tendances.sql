{{ config(materialized='table', schema='analytics') }}

WITH tech_exploded AS (
    SELECT
        o.id                            AS offre_id,
        o.date_publication,
        o.source,
        c.salaire_median,
        UNNEST(c.technologies)          AS technologie
    FROM raw.offres_emploi o
    JOIN clean.offres c ON o.id = c.raw_id
    WHERE c.technologies != '{}'
)

SELECT
    technologie,
    COUNT(*)                                    AS nb_mentions,
    COUNT(DISTINCT offre_id)                    AS nb_offres,
    ROUND(AVG(salaire_median))                  AS salaire_moyen,
    EXTRACT(YEAR FROM date_publication)         AS annee,
    EXTRACT(MONTH FROM date_publication)        AS mois
FROM tech_exploded
WHERE technologie IS NOT NULL
GROUP BY technologie, annee, mois
ORDER BY nb_mentions DESC

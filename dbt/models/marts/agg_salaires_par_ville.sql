{{ config(materialized='table', schema='analytics') }}

SELECT
    ville,
    COUNT(*)                            AS nb_offres,
    COUNT(salaire_median)               AS nb_avec_salaire,
    ROUND(AVG(salaire_median))          AS salaire_moyen,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salaire_median) AS salaire_median,
    MIN(salaire_median)                 AS salaire_min,
    MAX(salaire_median)                 AS salaire_max
FROM {{ ref('stg_offres') }}
WHERE ville != 'Inconnue'
  AND salaire_median IS NOT NULL
  AND salaire_median BETWEEN 15000 AND 200000
GROUP BY ville
HAVING COUNT(*) >= 3
ORDER BY nb_offres DESC

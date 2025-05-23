WITH gdp AS (
    SELECT * FROM {{ ref('stg_financial_data') }}
)
SELECT
    DATE_TRUNC('year', observation_date) AS year,
    AVG(value) AS avg_gdp
FROM gdp
GROUP BY 1

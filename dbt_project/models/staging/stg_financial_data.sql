WITH source AS (
    SELECT * FROM raw.financial_data
)
SELECT
    series_id,
    observation_date,
    value::numeric
FROM source

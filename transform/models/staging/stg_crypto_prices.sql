{{ config(materialized='view') }}

WITH unified_raw AS (
    -- Standardizing Live Data
    SELECT 
        coin_id,
        price,
        -- Converting Unix Epoch to Timestamp
        from_unixtime(CAST(timestamp AS DOUBLE)) AS observed_at,
        'live' AS data_source
    FROM {{ source('raw', 'raw_hourly_ingestion') }}

    UNION ALL

    -- Standardizing Historical Data
    SELECT 
        coin_id,
        price_usd AS price,
        -- Converting String Timestamp to actual Timestamp type
        CAST(timestamp AS TIMESTAMP) AS observed_at,
        'historical' AS data_source
    FROM {{ source('raw', 'raw_raw_historical') }}
),

deduplicated AS (
    SELECT 
        *,
        -- If we have two records for the same coin at the same time,
        -- this ranks them so we can pick just one.
        ROW_NUMBER() OVER (
            PARTITION BY coin_id, observed_at 
            ORDER BY data_source DESC -- Prioritizes 'live' over 'historical' if they overlap
        ) as row_num
    FROM unified_raw
)

SELECT 
    coin_id,
    price,
    observed_at,
    data_source
FROM deduplicated
WHERE row_num = 1
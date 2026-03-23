{{ config(materialized='view') }}

WITH unified_raw AS (
    -- Standardizing Live Data (Table 1)
    SELECT 
        coin_id,
        price,
        market_cap,
        from_unixtime(CAST(timestamp AS DOUBLE)) AS observed_at,
        'live' AS data_source
    FROM {{ source('raw', 'raw_hourly_ingestion') }}

    UNION ALL

    -- Standardizing Historical Data (Table 2)
    SELECT 
        coin_id,
        price_usd AS price, -- Mapping price_usd to price
        market_cap,
        CAST(timestamp AS TIMESTAMP) AS observed_at,
        'historical' AS data_source
    FROM {{ source('raw', 'raw_raw_historical') }}
),

deduplicated AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY coin_id, observed_at 
            ORDER BY data_source DESC 
        ) as row_num
    FROM unified_raw
)

SELECT 
    coin_id,
    price,
    market_cap,
    observed_at,
    data_source
FROM deduplicated
WHERE row_num = 1
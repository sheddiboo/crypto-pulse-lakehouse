{{ config(materialized='table') }} 
-- Materializes as a physical table in the Gold layer for optimized dashboard query performance

WITH base AS (
    SELECT 
        coin_id,
        price,
        -- Truncates timestamps to the nearest hour and applies a 1-hour shift to convert UTC to West Africa Time (WAT)
        DATE_TRUNC('hour', observed_at) + INTERVAL '1' HOUR AS observed_at
    FROM {{ ref('stg_crypto_prices') }}
),

metrics AS (
    SELECT 
        coin_id,
        price,
        observed_at,
        -- Calculates the rolling 24-hour moving average partitioned by individual asset
        AVG(price) OVER (
            PARTITION BY coin_id 
            ORDER BY observed_at 
            ROWS BETWEEN 24 PRECEDING AND CURRENT ROW
        ) AS moving_avg_24h
    FROM base
)

SELECT 
    *,
    -- Computes the percentage deviation of the current price against the 24-hour moving average
    (price - moving_avg_24h) / NULLIF(moving_avg_24h, 0) * 100 AS pct_change_24h
FROM metrics
-- Restricts the materialized output to the trailing 7 days to maintain a lean query profile for the dashboard
WHERE observed_at >= current_timestamp - INTERVAL '7' DAY
{{ config(materialized='table') }} 

WITH base AS (
    SELECT 
        coin_id,
        price,
        market_cap,
        -- Applying 1-hour shift to convert UTC to WAT
        observed_at + INTERVAL '1' HOUR AS observed_at
    FROM {{ ref('stg_crypto_prices') }}
),

metrics AS (
    SELECT 
        *,
        AVG(price) OVER (
            PARTITION BY coin_id 
            ORDER BY observed_at 
            ROWS BETWEEN 24 PRECEDING AND CURRENT ROW
        ) AS moving_avg_24h
    FROM base
)

SELECT 
    *,
    (price - moving_avg_24h) / NULLIF(moving_avg_24h, 0) * 100 AS pct_change_24h
FROM metrics
WHERE observed_at >= current_timestamp - INTERVAL '7' DAY
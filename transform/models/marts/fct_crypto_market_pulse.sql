{{ config(materialized='table') }} -- We use 'table' for Gold for faster dashboard performance

WITH base AS (
    SELECT * FROM {{ ref('stg_crypto_prices') }}
),

metrics AS (
    SELECT 
        coin_id,
        price,
        observed_at,
        -- Window function to get the average price of the last 24 hours
        AVG(price) OVER (
            PARTITION BY coin_id 
            ORDER BY observed_at 
            ROWS BETWEEN 24 PRECEDING AND CURRENT ROW
        ) as moving_avg_24h
    FROM base
)

SELECT 
    *,
    (price - moving_avg_24h) / NULLIF(moving_avg_24h, 0) * 100 as pct_change_24h
FROM metrics
WHERE observed_at >= current_timestamp - interval '7' day -- Keep the mart lean
-- Purpose: High-level daily KPI mart
-- Source: fact_orders
-- Grain: 1 row per day
-- Key Metrics: Gross Merchandise Value (GMV), Daily Active Users (DAU), Order volume

SELECT
    DATE(created_at) AS metric_date,
    COUNT(DISTINCT order_id) AS total_orders,
    SUM(total_amount) AS gmv,
    COUNT(DISTINCT customer_id) AS active_customers,
    COUNT(DISTINCT partner_id) AS active_partners
FROM
    fact_orders
WHERE
    status = 'COMPLETED'
GROUP BY
    DATE(created_at)
ORDER BY
    metric_date DESC;

-- Purpose: Core fact table for marketplace orders
-- Source: public.orders
-- Grain: 1 row per order
-- Key Metrics: Order status, total amount, completion time

SELECT
    id AS order_id,
    customer_id,
    partner_id,
    merchant_id,
    status,
    total_amount,
    created_at,
    updated_at,
    EXTRACT(EPOCH FROM (updated_at - created_at)) / 60 AS completion_time_minutes
FROM
    public.orders;

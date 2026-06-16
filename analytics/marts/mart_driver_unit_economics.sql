-- mart_driver_unit_economics.sql
-- Calculates profitability and utilization metrics for delivery partners

WITH partner_shifts AS (
    SELECT 
        partner_id,
        DATE_TRUNC('day', created_at) AS shift_date,
        COUNT(id) AS total_trips,
        SUM(fare_amount) AS total_fare_earnings,
        SUM(tip_amount) AS total_tips,
        SUM(distance_miles) AS total_distance
    FROM public.orders
    WHERE status = 'delivered'
    GROUP BY 1, 2
),
platform_fees AS (
    SELECT 
        partner_id,
        DATE_TRUNC('day', created_at) AS shift_date,
        SUM(platform_fee) AS total_platform_revenue
    FROM public.orders
    WHERE status = 'delivered'
    GROUP BY 1, 2
)
SELECT 
    s.shift_date,
    s.partner_id,
    s.total_trips,
    s.total_distance,
    s.total_fare_earnings + s.total_tips AS gross_earnings,
    (s.total_fare_earnings + s.total_tips) / NULLIF(s.total_trips, 0) AS earnings_per_trip,
    (s.total_fare_earnings + s.total_tips) / NULLIF(s.total_distance, 0) AS earnings_per_mile,
    f.total_platform_revenue,
    f.total_platform_revenue / NULLIF(s.total_fare_earnings + s.total_tips + f.total_platform_revenue, 0) AS platform_take_rate
FROM partner_shifts s
JOIN platform_fees f ON s.partner_id = f.partner_id AND s.shift_date = f.shift_date
WHERE s.total_trips > 0
ORDER BY s.shift_date DESC, s.total_trips DESC;

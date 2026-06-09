-- Purpose: Customer dimensional table
-- Source: public.users, public.customer_profiles
-- Grain: 1 row per customer
-- Key Metrics: Lifetime rides, total spend, churn risk segment

SELECT
    u.id AS customer_id,
    u.email,
    u.created_at AS signup_date,
    COALESCE(c.lifetime_rides, 0) AS lifetime_rides,
    COALESCE(c.total_spend, 0.0) AS total_spend,
    CASE 
        WHEN c.last_ride_date < CURRENT_DATE - INTERVAL '30 days' THEN 'At Risk'
        ELSE 'Active'
    END AS churn_risk_segment
FROM
    public.users u
LEFT JOIN
    public.customer_profiles c ON u.id = c.user_id
WHERE
    u.role = 'CUSTOMER';

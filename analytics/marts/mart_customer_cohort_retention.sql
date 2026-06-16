-- mart_customer_cohort_retention.sql
-- Analyzes user retention by monthly cohort

WITH customer_first_order AS (
    SELECT 
        customer_id,
        DATE_TRUNC('month', MIN(created_at)) AS cohort_month
    FROM public.orders
    GROUP BY 1
),
order_activity AS (
    SELECT 
        o.customer_id,
        DATE_TRUNC('month', o.created_at) AS activity_month,
        COUNT(o.id) AS monthly_orders,
        SUM(p.amount) AS monthly_spend
    FROM public.orders o
    JOIN public.payments p ON o.id = p.order_id
    WHERE p.status = 'succeeded'
    GROUP BY 1, 2
),
cohort_size AS (
    SELECT 
        cohort_month,
        COUNT(DISTINCT customer_id) AS total_customers
    FROM customer_first_order
    GROUP BY 1
)
SELECT 
    c.cohort_month,
    s.total_customers,
    a.activity_month,
    EXTRACT(MONTH FROM AGE(a.activity_month, c.cohort_month)) AS months_since_first_order,
    COUNT(DISTINCT a.customer_id) AS retained_customers,
    ROUND(COUNT(DISTINCT a.customer_id)::numeric / s.total_customers, 4) AS retention_rate,
    SUM(a.monthly_spend) AS cohort_revenue
FROM customer_first_order c
JOIN order_activity a ON c.customer_id = a.customer_id
JOIN cohort_size s ON c.cohort_month = s.cohort_month
GROUP BY 1, 2, 3, 4
ORDER BY 1, 3;

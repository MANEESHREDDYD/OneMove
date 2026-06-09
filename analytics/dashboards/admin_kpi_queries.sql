-- Purpose: Queries for Admin Command Center Dashboard
-- Metrics: Real-time GMV, Active Partners

-- 1. Real-time Gross Merchandise Value (Today)
SELECT 
    SUM(total_amount) AS gmv_today
FROM 
    public.orders
WHERE 
    DATE(created_at) = CURRENT_DATE
    AND status IN ('COMPLETED', 'IN_PROGRESS');

-- 2. Active Partners Online
SELECT 
    COUNT(DISTINCT id) AS active_partners
FROM 
    public.partner_profiles
WHERE 
    is_online = TRUE;

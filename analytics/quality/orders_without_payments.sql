-- Purpose: Data quality check identifying completed orders missing a payment record
-- Expected Output: 0 rows

SELECT 
    o.id AS order_id,
    o.status
FROM 
    public.orders o
LEFT JOIN 
    public.payments p ON o.id = p.order_id
WHERE 
    o.status = 'COMPLETED'
    AND p.id IS NULL;

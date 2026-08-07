# 11 PERFORMANCE & CONCURRENCY AUDIT

## 1. Database Indexes (Missing)
- **No Foreign Key Indexes**: The database schema (`supabase/migrations/00000_schema.sql`) completely lacks `CREATE INDEX` statements.
- **Impact**: All heavily-used foreign keys (e.g., `owner_id` on `merchants`, `customer_id` and `driver_id` on `orders`, `product_id` on `order_items`) will cause full sequential scans during lookups or `JOIN`s. As data volume grows, these unindexed relations will result in severe performance degradation and database lockups.

## 2. Asynchronous Waterfalls
- **Sequential Data Fetching**: Instead of parallelizing independent database calls, several core backend routes await queries sequentially.
- **Example - Command Center (`app/admin/command-center/page.tsx`)**:
  ```typescript
  // Waterfall pattern - these queries block each other sequentially
  const { data: rpcData } = await supabase.rpc('get_admin_dashboard_metrics')
  const { data: ordersData } = await supabase.from('orders').select('*').limit(50)
  const { data: merchantsData } = await supabase.from('merchants').select('*')
  ```
- **Example - ML Lab (`app/admin/ml-lab/actions.ts`)**:
  ```typescript
  // Waterfall pattern
  const { data: orders } = await supabase.from('orders').select('total_amount');
  const { data: payouts } = await supabase.from('merchant_payouts').select('amount');
  ```
- **Recommendation**: Wrap these independent, non-dependent queries in `Promise.all` to execute them concurrently. This will drastically reduce server-side rendering latency and improve the Time to First Byte (TTFB).

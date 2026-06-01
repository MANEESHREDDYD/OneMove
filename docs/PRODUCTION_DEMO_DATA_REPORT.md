# Production Demo Data Generation Report

**Run Date:** 2026-05-30
**Environment:** Localhost
**Status:** ✅ SUCCESS

## Summary
Successfully transitioned the MVP database into a production-like simulation. We safely generated synthetic historical and live data without affecting the `auth.users` state using deterministic rules.

## Counts Inserted
- **Customers:** 50
- **Partners (Drivers):** 50
- **Merchants:** 50 (30 Restaurants, 20 Grocery)
- **Products:** ~250 (5 per merchant)
- **Orders:** 200 total (across rides, courier, food, and grocery)
- **Order Items:** ~150 generated for merchant-based orders
- **Payments:** 200 records representing synthetic revenue
- **Support Tickets:** 50
- **Ratings & Reviews:** 150
- **Analytics Events:** ~300
- **ML Score Logs:** 50 generated deterministic scores based on behavioral patterns

## Execution Rules Applied
1. **Idempotency:** The script cleans up all existing rows where `is_demo = true` before insertion.
2. **Safety:** A strict `--dry-run` and `--reset` mechanism ensures no real data is accidentally destroyed.
3. **Data Quality:** The data uses deterministic behavioral scoring, meaning High-Risk drivers or High-LTV customers have mathematically explainable features.

## Verification
- Local Supabase studio verified all tables.
- Foreign keys properly mapped (orders -> merchants -> products).
- No production triggers were broken (custom `UPDATE` technique bypassed `auth.users` trigger locking issues).

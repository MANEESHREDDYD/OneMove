# 08 DATABASE AND RLS AUDIT

## 1. Schema vs Types Reconciliation
- **Synchronization**: `supabase/schema.sql` and `types/database.types.ts` are heavily synchronized. Enums (`user_role`, `merchant_category`, `service_type`, `order_status`, `vehicle_type`, `payment_status`) match exactly.
- **Data Types**: The column types correctly map between Postgres types (e.g., `NUMERIC`, `JSONB`) and TypeScript types (`number`, `Json`).
- **Actual Queries**: A review of Supabase `.select()`, `.insert()`, and `.update()` calls across the `app/` directory aligns with the defined schema, using the generated type definitions safely. No raw SQL mismatches were found.

## 2. RLS Policies Audit
- **Permissive Base Policies**: The `policies.sql` file implements "MVP permissive rules for demo purposes", which are overly broad and fail to isolate cross-tenant data.
- **Subquery Performance**: Several policies use `EXISTS (SELECT 1 FROM ...)` which is functionally correct for cross-table permission checks (e.g., checking if a merchant owner can view their products/orders) but may cause performance degradation at scale without proper indexing.
- **Missing Column-Level Restrictions**: `UPDATE` policies (e.g., on `profiles` and `orders`) apply to the entire row, allowing unauthorized modification of sensitive columns by the users themselves.

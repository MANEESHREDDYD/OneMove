# 03 DATABASE MIGRATION VERIFICATION

## Migration Inventory

1. **`00000_schema.sql`**
   * Legacy OneMove tables: profiles, merchants, products, vehicles, orders, order_items, payments, tracking.
   * Legacy permissive RLS policies.
2. **`00001_auth_trigger.sql`**
   * Initial auth trigger for propagating users.
3. **`00002_zonepilot_v151.sql`**
   * Drops legacy permissive RLS tracking policies.
   * Hardens `00001_auth_trigger.sql` function to stop metadata minting.
   * Creates the v1.5.1 core: `studies`, `participants`, `participant_roles`, `assignments`, `volunteer_orders`, `volunteer_order_events`, `operational_events`, `dataset_registry`, `consent_log`, `collector_runs`, `weather_observations`, `traffic_observations`.
   * Strictest RLS (admin-only fallback) implemented on all new tables.
   * Added `check_total_amount_nonnegative` constraints.
   * `provenance_type` Enum established.
4. **`00003_fix_rls_recursion.sql`**
   * Explicit `public.is_admin()` SECURITY DEFINER function to fix infinite recursion in `00000_schema.sql` legacy profiles policies.

*The `supabase/fixes/*.sql` directory was left untouched and unapplied because they represent ad-hoc drift fixes rather than canonical structure. ZonePilot relies entirely on canonical, ordered migrations.*

## Fresh Reset Verification

```text
> npx -y supabase db reset
Resetting local database...
Recreating database...
Initialising schema...
Seeding globals from roles.sql...
Applying migration 00000_schema.sql...
Applying migration 00001_auth_trigger.sql...
Applying migration 00002_zonepilot_v151.sql...
Applying migration 00003_fix_rls_recursion.sql...
Seeding data from supabase/seed.sql...
Restarting containers...
Finished supabase db reset on branch main.
```

## Schema Drift Verification

```text
> npx -y supabase db diff
Creating shadow database...
Initialising schema...
Seeding globals from roles.sql...
Applying migration 00000_schema.sql...
Applying migration 00001_auth_trigger.sql...
Applying migration 00002_zonepilot_v151.sql...
Applying migration 00003_fix_rls_recursion.sql...
Diffing schemas...
Finished supabase db diff on branch main.

No schema changes found
```

## Conclusion

- Canonical state successfully ordered.
- Fresh local resets execute cleanly and reproduce the expected state precisely.
- No drift between local migrations and the running shadow/local database instance.

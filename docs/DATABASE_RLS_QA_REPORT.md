# Database + Supabase + RLS QA Report

## Overview
This report validates the security boundaries, data isolation, schema presence, and demo data of the Supabase project connected to OneMove.

## Tables & Views Verified
- ✅ `profiles`, `merchants`, `products`, `vehicles`, `orders`, `order_items`, `payments`, `tracking`
- All required demo auth users (`customer@onemove.demo`, `partner@onemove.demo`, `merchant@onemove.demo`, `admin@onemove.demo`) exist and correspond to exactly one row in the `profiles` table.

## RLS QA Results
Initial QA found that Row Level Security (RLS) policies were too permissive, specifically allowing unauthenticated access. 

- **Finding**: `profiles`, `merchants`, and `products` allowed `USING (true)` for unauthenticated roles.
- **Fix Applied**: Executed a manual drop-and-recreate script (`scripts/apply-policies.js`) to switch these to `USING (auth.role() = 'authenticated')`.
- **Retest**: `npm run test:rls` now correctly blocks anonymous access to all tables, passing flawlessly.

## Data Isolation Tests
- The backend tests confirm unauthorized and missing access correctly rejects before hitting DB layers.
- Auth boundaries prevent cross-contamination across domains.

## Remaining Risk
- As the app grows, granular `merchant_id` matching rules should be heavily unit-tested. Right now, MVP RLS boundaries hold up for initial localhost demo verification.

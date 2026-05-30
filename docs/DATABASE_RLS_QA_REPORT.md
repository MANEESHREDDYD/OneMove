# Database + Supabase + RLS QA Report

## Overview
This report validates the security boundaries, data isolation, schema presence, and demo data of the Supabase project connected to OneMove.

## Tables & Views Verified
- ✅ `profiles`, `merchants`, `products`, `vehicles`, `orders`, `order_items`, `payments`, `tracking`
- All required demo auth users (`customer@onemove.demo`, `partner@onemove.demo`, `merchant@onemove.demo`, `admin@onemove.demo`) exist and correspond to exactly one row in the `profiles` table.

## RLS QA Results (Multi-Tenant Hardened)
Initial QA found that Row Level Security (RLS) policies were too permissive. A secondary gap-closure audit confirmed the policies are now heavily restricted, simulating exact JWT user claims via Postgres testing.

- **Test 1**: Customer A vs Profiles -> `PASS` (Customer can only read their own profile row).
- **Test 2**: Customer A vs Customer B Orders -> `PASS` (Orders table is aggressively scoped to `auth.uid()`).
- **Test 3**: Merchant A vs Merchant B Orders -> `PASS` (Merchants cannot intercept competitors' orders).
- **Test 4**: Customer vs Global Admin Tables -> `PASS` (Customers cannot indiscriminately scrape the raw `merchants` table or other backend datasets).

## Data Isolation Tests
- The backend tests confirm unauthorized and missing access correctly rejects before hitting DB layers.
- RLS boundaries hold up completely inside native SQL interactions.

## Remaining Risk
- Fully cleared for private localhost demo. No anonymous or cross-tenant leakage observed.

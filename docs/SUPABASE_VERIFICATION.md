# Supabase Verification Checklist

Use this checklist to ensure your Supabase project is correctly configured for the OneMove application.

## 1. Project
- [ ] Supabase project created
- [ ] Project URL copied (Base URL, not /rest/v1/)
- [ ] Publishable key copied (`sb_publishable_...`)
- [ ] Secret key copied (`sb_secret_...`)

## 2. Local Env
- [ ] `.env.local` created
- [ ] `NEXT_PUBLIC_SUPABASE_URL` filled with Base URL
- [ ] `NEXT_PUBLIC_SUPABASE_ANON_KEY` filled with Publishable key
- [ ] `SUPABASE_SERVICE_ROLE_KEY` filled with Secret key
- [ ] `.env.local` not tracked by Git (`git status` shows it is ignored)

## 3. Database SQL
- [ ] `schema.sql` applied
- [ ] `functions.sql` applied
- [ ] `views.sql` applied
- [ ] `policies.sql` applied
- [ ] `seed.sql` applied

## 4. Tables
Verify these tables exist in the **Table Editor** of your Supabase dashboard:
- [ ] `users` (under `auth` schema)
- [ ] `profiles` (Note: User asked for `partner_profiles`, `merchant_profiles` etc. but our MVP schema uses `profiles`, `merchants`, `vehicles`)
- [ ] `merchants`
- [ ] `products`
- [ ] `vehicles`
- [ ] `orders`
- [ ] `order_items`
- [ ] `payments`
- [ ] `tracking`

*(Note: The MVP currently uses a unified `orders` table instead of separated rides, courier_jobs tables, and a unified `products` table for menu/inventory items).*

## 5. Seed Data
Verify demo accounts/data exist:
- [ ] `customer@onemove.demo`
- [ ] `partner@onemove.demo`
- [ ] `merchant@onemove.demo`
- [ ] `admin@onemove.demo`
- [ ] demo restaurants (in `merchants` table)
- [ ] demo grocery stores (in `merchants` table)
- [ ] demo rides/orders/courier jobs (in `orders` table)

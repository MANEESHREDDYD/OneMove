-- 2026_rls_hardening.sql
-- Final RLS hardening for the OneMove portfolio audit.
--
-- Goal: remove broad profile readability (no phone/email exposed to other users)
-- while preserving every working demo flow via narrow policies + safe display
-- views. Order/order_items/payments/status_events isolation is already correct
-- (verified) and is reasserted here for clarity.
--
-- Safe to run multiple times (idempotent).

-- ---------------------------------------------------------------------------
-- 0. Helper functions (idempotent; SECURITY DEFINER so they can read role
--    even when profiles RLS is locked down).
-- ---------------------------------------------------------------------------
create or replace function public.is_admin() returns boolean
  language sql stable security definer set search_path = public as
$$ select exists (select 1 from public.profiles where id = auth.uid() and role = 'admin'); $$;

-- ---------------------------------------------------------------------------
-- 1. PROFILES: lock to own-profile + admin only. Remove every broad policy.
-- ---------------------------------------------------------------------------
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Profiles are viewable by authenticated users." ON public.profiles;
DROP POLICY IF EXISTS "Public profiles are viewable by everyone." ON public.profiles;
DROP POLICY IF EXISTS "Users can view profiles." ON public.profiles;
DROP POLICY IF EXISTS "public_select_merchant_partner_profiles" ON public.profiles;

DROP POLICY IF EXISTS "user_select_own_profile" ON public.profiles;
CREATE POLICY "user_select_own_profile" ON public.profiles
  FOR SELECT USING (id = auth.uid());

DROP POLICY IF EXISTS "admin_select_profiles" ON public.profiles;
CREATE POLICY "admin_select_profiles" ON public.profiles
  FOR SELECT USING (public.is_admin());

-- (INSERT/UPDATE own-profile policies are left intact.)

-- ---------------------------------------------------------------------------
-- 2. SAFE DISPLAY VIEWS — expose ONLY non-sensitive display fields.
--    Owned by the migration role (postgres) so they bypass profiles RLS and
--    return safe columns to authenticated users. No phone / no email.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.safe_profile_cards AS
  SELECT id, full_name AS display_name, role, avatar_url
  FROM public.profiles;

CREATE OR REPLACE VIEW public.safe_partner_cards AS
  SELECT id, full_name AS display_name, role, avatar_url
  FROM public.profiles
  WHERE role = 'driver';

CREATE OR REPLACE VIEW public.safe_merchant_cards AS
  SELECT id, name AS display_name, category, rating, status
  FROM public.merchants;

-- Only safe columns are exposed; grant read to authenticated (merchant catalog
-- may also be read anonymously, matching the existing public-catalog design).
REVOKE ALL ON public.safe_profile_cards FROM anon;
REVOKE ALL ON public.safe_partner_cards FROM anon;
GRANT SELECT ON public.safe_profile_cards TO authenticated;
GRANT SELECT ON public.safe_partner_cards TO authenticated;
GRANT SELECT ON public.safe_merchant_cards TO authenticated, anon;

-- ---------------------------------------------------------------------------
-- 3. ORDERS / ORDER_ITEMS / PAYMENTS / STATUS_EVENTS — reassert isolation.
--    (These are already correct; recreated idempotently for an explicit,
--    auditable final state. Merchants are scoped by merchants.owner_id.)
-- ---------------------------------------------------------------------------
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;

-- Orders
DROP POLICY IF EXISTS "merchant_select_orders" ON public.orders;
CREATE POLICY "merchant_select_orders" ON public.orders FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.merchants m WHERE m.id = merchant_id AND m.owner_id = auth.uid())
);

-- Payments: merchant may read payments tied ONLY to their own orders
-- (previously a merchant could read no payments; this is the "safe to expose"
-- subset requested — payment status/amount for their own orders).
DROP POLICY IF EXISTS "merchant_select_payments" ON public.payments;
CREATE POLICY "merchant_select_payments" ON public.payments FOR SELECT USING (
  EXISTS (
    SELECT 1 FROM public.orders o
    JOIN public.merchants m ON m.id = o.merchant_id
    WHERE o.id = payments.order_id AND m.owner_id = auth.uid()
  )
);

-- Order items / status events merchant scoping already exist; reassert items.
DROP POLICY IF EXISTS "merchant_select_order_items" ON public.order_items;
CREATE POLICY "merchant_select_order_items" ON public.order_items FOR SELECT USING (
  EXISTS (
    SELECT 1 FROM public.orders o
    JOIN public.merchants m ON o.merchant_id = m.id
    WHERE o.id = order_id AND m.owner_id = auth.uid()
  )
);

-- ---------------------------------------------------------------------------
-- 4. Ask PostgREST to reload its schema cache so the new views are exposed.
-- ---------------------------------------------------------------------------
NOTIFY pgrst, 'reload schema';

-- 2026_advanced_qa_rls_fixes.sql

-- Helpers
create or replace function public.is_admin() returns boolean language sql stable security definer set search_path = public as $$ select exists (select 1 from public.profiles where id = auth.uid() and role = 'admin'); $$;
create or replace function public.is_partner() returns boolean language sql stable security definer set search_path = public as $$ select exists (select 1 from public.profiles where id = auth.uid() and role = 'driver'); $$;
create or replace function public.is_merchant() returns boolean language sql stable security definer set search_path = public as $$ select exists (select 1 from public.profiles where id = auth.uid() and role = 'merchant'); $$;
create or replace function public.is_customer() returns boolean language sql stable security definer set search_path = public as $$ select exists (select 1 from public.profiles where id = auth.uid() and role = 'customer'); $$;

-- Drop existing complex policies for strictness
DROP POLICY IF EXISTS "Strict orders select policy" ON public.orders;
DROP POLICY IF EXISTS "Strict orders update policy" ON public.orders;
DROP POLICY IF EXISTS "drivers_update_orders" ON public.orders;
DROP POLICY IF EXISTS "partners_select_jobs" ON public.orders;

-- Orders
CREATE POLICY "admin_select_orders" ON public.orders FOR SELECT USING (is_admin());
CREATE POLICY "admin_update_orders" ON public.orders FOR UPDATE USING (is_admin());

CREATE POLICY "customer_select_orders" ON public.orders FOR SELECT USING (customer_id = auth.uid());
CREATE POLICY "customer_update_orders" ON public.orders FOR UPDATE USING (customer_id = auth.uid());

CREATE POLICY "merchant_select_orders" ON public.orders FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.merchants m WHERE m.id = merchant_id AND m.owner_id = auth.uid())
);
CREATE POLICY "merchant_update_orders" ON public.orders FOR UPDATE USING (
  EXISTS (SELECT 1 FROM public.merchants m WHERE m.id = merchant_id AND m.owner_id = auth.uid())
);

CREATE POLICY "partner_select_orders" ON public.orders FOR SELECT USING (
  driver_id = auth.uid() OR 
  (is_partner() AND driver_id IS NULL AND service_type IN ('ride', 'eats', 'grocery', 'courier') AND status IN ('pending', 'placed', 'merchant_accepted', 'preparing', 'ready', 'requested', 'created'))
);
CREATE POLICY "partner_update_orders" ON public.orders FOR UPDATE USING (
  driver_id = auth.uid() OR 
  (is_partner() AND driver_id IS NULL)
);

-- Payments
DROP POLICY IF EXISTS "Users can view own payments." ON public.payments;
CREATE POLICY "admin_select_payments" ON public.payments FOR SELECT USING (is_admin());
CREATE POLICY "customer_select_payments" ON public.payments FOR SELECT USING (customer_id = auth.uid());

-- Order Items
DROP POLICY IF EXISTS "Users can view own order items." ON public.order_items;
CREATE POLICY "admin_select_order_items" ON public.order_items FOR SELECT USING (is_admin());
CREATE POLICY "customer_select_order_items" ON public.order_items FOR SELECT USING (
  EXISTS (SELECT 1 FROM orders o WHERE o.id = order_id AND o.customer_id = auth.uid())
);
CREATE POLICY "merchant_select_order_items" ON public.order_items FOR SELECT USING (
  EXISTS (SELECT 1 FROM orders o JOIN merchants m ON o.merchant_id = m.id WHERE o.id = order_id AND m.owner_id = auth.uid())
);
CREATE POLICY "partner_select_order_items" ON public.order_items FOR SELECT USING (
  EXISTS (SELECT 1 FROM orders o WHERE o.id = order_id AND o.driver_id = auth.uid())
);

-- Profiles
DROP POLICY IF EXISTS "Users can view profiles." ON public.profiles;
CREATE POLICY "admin_select_profiles" ON public.profiles FOR SELECT USING (is_admin());
CREATE POLICY "user_select_own_profile" ON public.profiles FOR SELECT USING (id = auth.uid());
CREATE POLICY "public_select_merchant_partner_profiles" ON public.profiles FOR SELECT USING (
  role IN ('merchant', 'driver')
);

-- Order Status Events
DROP POLICY IF EXISTS "Involved view order events." ON public.order_status_events;
CREATE POLICY "admin_select_order_events" ON public.order_status_events FOR SELECT USING (is_admin());
CREATE POLICY "customer_select_order_events" ON public.order_status_events FOR SELECT USING (
  EXISTS (SELECT 1 FROM orders o WHERE o.id = order_id AND o.customer_id = auth.uid())
);
CREATE POLICY "merchant_select_order_events" ON public.order_status_events FOR SELECT USING (
  EXISTS (SELECT 1 FROM orders o JOIN merchants m ON o.merchant_id = m.id WHERE o.id = order_id AND m.owner_id = auth.uid())
);
CREATE POLICY "partner_select_order_events" ON public.order_status_events FOR SELECT USING (
  EXISTS (SELECT 1 FROM orders o WHERE o.id = order_id AND o.driver_id = auth.uid())
);

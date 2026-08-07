CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid() AND role = 'admin'
  );
$$ LANGUAGE sql SECURITY DEFINER SET search_path = public;

-- Drop all profile policies and recreate safely
DROP POLICY IF EXISTS "Users view own profile, admins view all." ON profiles;
CREATE POLICY "Users view own profile, admins view all." ON profiles FOR SELECT
USING (
  auth.uid() = id OR public.is_admin()
);

DROP POLICY IF EXISTS "Admins can update any profile." ON profiles;
CREATE POLICY "Admins can update any profile." ON profiles FOR UPDATE
USING (public.is_admin());

DROP POLICY IF EXISTS "Users can update own profile except role." ON profiles;
CREATE POLICY "Users can update own profile except role." ON profiles FOR UPDATE
USING (auth.uid() = id AND NOT public.is_admin())
WITH CHECK (
  auth.uid() = id AND role = (SELECT role FROM profiles WHERE id = auth.uid()) 
);

-- And tracking policy
DROP POLICY IF EXISTS "Tracking data is viewable by admins and relevant users." ON tracking;
CREATE POLICY "Tracking data is viewable by admins and relevant users." ON tracking FOR SELECT
USING (
  public.is_admin() OR driver_id = auth.uid()
);

-- study policies
DROP POLICY IF EXISTS "Admins have full access to study tables" ON studies;
CREATE POLICY "Admins have full access to study tables" ON studies FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Admins have full access to participants" ON participants;
CREATE POLICY "Admins have full access to participants" ON participants FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Admins have full access to volunteer_orders" ON volunteer_orders;
CREATE POLICY "Admins have full access to volunteer_orders" ON volunteer_orders FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Admins have full access to volunteer_order_events" ON volunteer_order_events;
CREATE POLICY "Admins have full access to volunteer_order_events" ON volunteer_order_events FOR ALL USING (public.is_admin());

DROP POLICY IF EXISTS "Admins have full access to operational_events" ON operational_events;
CREATE POLICY "Admins have full access to operational_events" ON operational_events FOR ALL USING (public.is_admin());

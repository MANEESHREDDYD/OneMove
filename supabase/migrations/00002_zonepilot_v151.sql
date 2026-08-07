-- ZonePilot v1.5.1 Schema & Security Hardening
-- FR-2 & FR-3 Canonical Migration

-- 1. Revoke insecure tracking policies
DROP POLICY IF EXISTS "Tracking data is public for active orders." ON tracking;
CREATE POLICY "Tracking data is viewable by admins and relevant users." ON tracking FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin', 'merchant')
  ) OR driver_id = auth.uid()
);

-- 2. Revoke insecure cross-tenant profile reads
DROP POLICY IF EXISTS "Public profiles are viewable by everyone." ON profiles;
CREATE POLICY "Users view own profile, admins view all." ON profiles FOR SELECT
USING (
  auth.uid() = id OR 
  EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin')
);

-- 3. Lock down profile role modifications (only admin can change roles)
DROP POLICY IF EXISTS "Users can update own profile." ON profiles;
CREATE POLICY "Users can update own profile except role." ON profiles FOR UPDATE
USING (auth.uid() = id)
WITH CHECK (
  auth.uid() = id AND role = (SELECT role FROM profiles WHERE id = auth.uid()) 
);
-- Admins can update any profile including roles
CREATE POLICY "Admins can update any profile." ON profiles FOR UPDATE
USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));

-- 4. Prevent arbitrary financial/ownership mutations
DROP POLICY IF EXISTS "Involved parties can update orders." ON orders;
CREATE POLICY "Users can only update specific non-financial order fields." ON orders FOR UPDATE
USING (auth.uid() = customer_id OR auth.uid() = driver_id)
WITH CHECK (
  (auth.uid() = customer_id OR auth.uid() = driver_id) AND
  total_amount = (SELECT total_amount FROM orders WHERE id = orders.id) AND
  customer_id = (SELECT customer_id FROM orders WHERE id = orders.id)
);


-- ==========================================
-- ZonePilot v1.5.1 Schema Additions
-- ==========================================

-- Provenance Enum
CREATE TYPE provenance_type AS ENUM (
  'OBSERVED', 'DERIVED', 'ESTIMATED', 'SIMULATED', 'PUBLIC_BENCHMARK', 'MERCHANT_CONFIDENTIAL', 'DEMO_SYNTHETIC', 'ASSUMPTION'
);

CREATE TABLE studies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  city TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  ended_at TIMESTAMPTZ,
  protocol_version TEXT NOT NULL,
  experiment_protocol_hash TEXT,
  observation_protocol_hash TEXT,
  governance_version TEXT,
  status TEXT NOT NULL DEFAULT 'planned',
  final_snapshot_id TEXT
);

CREATE TABLE participants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id TEXT NOT NULL UNIQUE,
  hash_key_version TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE participant_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('OBSERVER', 'VOLUNTEER', 'OWNER')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(participant_id, role)
);

CREATE TABLE assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
  participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE volunteer_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
  participant_id UUID NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE volunteer_order_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES volunteer_orders(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL,
  provenance provenance_type NOT NULL,
  supersedes_id UUID,
  correction_reason TEXT,
  record_status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (record_status IN ('ACTIVE', 'SUPERSEDED', 'WITHDRAWN')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE operational_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL,
  provenance provenance_type NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE dataset_registry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_name TEXT NOT NULL,
  version TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE consent_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  participant_id UUID NOT NULL REFERENCES participants(id),
  consented_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  consent_version TEXT NOT NULL
);

-- Operational Tables for Collectors
CREATE TABLE collector_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  collector_name TEXT NOT NULL,
  scheduled_for TIMESTAMPTZ NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'running',
  records_collected INT DEFAULT 0
);

CREATE TABLE weather_observations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID REFERENCES collector_runs(id),
  temperature NUMERIC NOT NULL,
  precipitation NUMERIC NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE traffic_observations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID REFERENCES collector_runs(id),
  congestion_level NUMERIC NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL
);

-- Check constraints as requested
ALTER TABLE orders ADD CONSTRAINT check_total_amount_nonnegative CHECK (total_amount >= 0);
ALTER TABLE payments ADD CONSTRAINT check_payment_amount_nonnegative CHECK (amount >= 0);

-- Enable RLS on new tables
ALTER TABLE studies ENABLE ROW LEVEL SECURITY;
ALTER TABLE participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE participant_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE volunteer_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE volunteer_order_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE operational_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE dataset_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE collector_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE weather_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE traffic_observations ENABLE ROW LEVEL SECURITY;

-- Secure Defaults: ONLY ADMINS can access study tables by default. Machine jobs will bypass RLS.
CREATE POLICY "Admins have full access to study tables" ON studies FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
CREATE POLICY "Admins have full access to participants" ON participants FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
CREATE POLICY "Admins have full access to volunteer_orders" ON volunteer_orders FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
CREATE POLICY "Admins have full access to volunteer_order_events" ON volunteer_order_events FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
CREATE POLICY "Admins have full access to operational_events" ON operational_events FOR ALL USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));

-- View for volunteer orders current state
CREATE VIEW volunteer_orders_current AS
SELECT 
  o.id,
  o.study_id,
  o.participant_id,
  (SELECT event_type FROM volunteer_order_events e WHERE e.order_id = o.id AND e.record_status = 'ACTIVE' ORDER BY occurred_at DESC LIMIT 1) as current_status,
  (SELECT occurred_at FROM volunteer_order_events e WHERE e.order_id = o.id AND e.record_status = 'ACTIVE' ORDER BY occurred_at DESC LIMIT 1) as last_updated
FROM volunteer_orders o;

-- Fix Auth Trigger to prevent role minting via raw_user_meta_data
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, role)
  VALUES (
    new.id,
    COALESCE(new.raw_user_meta_data->>'name', 'New User'),
    'customer' -- FORCE customer role, ignoring metadata
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

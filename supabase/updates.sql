-- Production Demo Enhancements Schema Updates

-- 1. Alter existing tables to support demo tagging
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT false;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS seed_run_id TEXT;

ALTER TABLE merchants ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT false;
ALTER TABLE merchants ADD COLUMN IF NOT EXISTS seed_run_id TEXT;

ALTER TABLE products ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT false;
ALTER TABLE products ADD COLUMN IF NOT EXISTS seed_run_id TEXT;

ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT false;
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS seed_run_id TEXT;

ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT false;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS seed_run_id TEXT;

ALTER TABLE order_items ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT false;
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS seed_run_id TEXT;

ALTER TABLE payments ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT false;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS seed_run_id TEXT;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS method TEXT DEFAULT 'card';

-- 2. Create new tables for full marketplace depth

-- Support Tickets
CREATE TABLE IF NOT EXISTS support_tickets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
  subject TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  is_demo BOOLEAN DEFAULT false,
  seed_run_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own support tickets." ON support_tickets FOR SELECT USING (auth.uid() = customer_id);

-- Ratings and Reviews
CREATE TABLE IF NOT EXISTS ratings_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
  reviewer_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  target_id UUID NOT NULL, -- Generic ID (merchant or partner)
  target_type TEXT NOT NULL, -- 'merchant', 'driver'
  rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
  comment TEXT,
  is_demo BOOLEAN DEFAULT false,
  seed_run_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE ratings_reviews ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public ratings." ON ratings_reviews FOR SELECT USING (true);

-- Partner Earnings
CREATE TABLE IF NOT EXISTS partner_earnings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  order_id UUID REFERENCES orders(id) ON DELETE SET NULL,
  amount NUMERIC(10, 2) NOT NULL,
  description TEXT,
  is_demo BOOLEAN DEFAULT false,
  seed_run_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE partner_earnings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Partners can view own earnings." ON partner_earnings FOR SELECT USING (auth.uid() = partner_id);

-- Merchant Payouts
CREATE TABLE IF NOT EXISTS merchant_payouts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
  amount NUMERIC(10, 2) NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  period_start TIMESTAMPTZ,
  period_end TIMESTAMPTZ,
  is_demo BOOLEAN DEFAULT false,
  seed_run_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE merchant_payouts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Merchants view own payouts." ON merchant_payouts FOR SELECT USING (
  EXISTS (SELECT 1 FROM merchants m WHERE m.id = merchant_payouts.merchant_id AND m.owner_id = auth.uid())
);

-- Analytics Events
CREATE TABLE IF NOT EXISTS analytics_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,
  user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
  metadata JSONB,
  is_demo BOOLEAN DEFAULT false,
  seed_run_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;
-- No public select, admin only

-- ML Score Logs
CREATE TABLE IF NOT EXISTS ml_score_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  score_type TEXT NOT NULL,
  target_id UUID NOT NULL, -- Which user/order it relates to
  score_value NUMERIC NOT NULL,
  metadata JSONB,
  is_demo BOOLEAN DEFAULT false,
  seed_run_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE ml_score_logs ENABLE ROW LEVEL SECURITY;
-- No public select, admin only

-- Order Status Events
CREATE TABLE IF NOT EXISTS order_status_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  status TEXT NOT NULL,
  notes TEXT,
  is_demo BOOLEAN DEFAULT false,
  seed_run_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE order_status_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Involved view order events." ON order_status_events FOR SELECT USING (
  EXISTS (SELECT 1 FROM orders o WHERE o.id = order_status_events.order_id AND (o.customer_id = auth.uid() OR o.driver_id = auth.uid()))
);

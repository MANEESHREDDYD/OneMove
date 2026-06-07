-- Phase 4 Intelligence Schema

-- 1. ops_insights
CREATE TABLE IF NOT EXISTS public.ops_insights (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  severity text NOT NULL, -- HIGH, MEDIUM, LOW
  category text NOT NULL, -- overdue_order, unassigned_ready_order, demand_surge, partner_shortage, merchant_delay, high_risk_order, refund_spike, low_trust_partner, data_quality_failure
  source_table text NOT NULL,
  source_id uuid, -- Can be null if it's a general insight
  entity_id uuid, -- Merchant or partner or customer ID this relates to
  features jsonb DEFAULT '{}'::jsonb,
  explanation text NOT NULL,
  recommended_action text NOT NULL,
  is_reviewed boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. support_tickets
CREATE TABLE IF NOT EXISTS public.support_tickets (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  customer_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  order_id uuid REFERENCES public.orders(id) ON DELETE CASCADE,
  category text NOT NULL,
  priority text NOT NULL DEFAULT 'LOW',
  status text NOT NULL DEFAULT 'OPEN',
  description text NOT NULL,
  assistant_explanation text,
  recommended_action text,
  refund_eligibility boolean DEFAULT false,
  escalation_required boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
  updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. experiments
CREATE TABLE IF NOT EXISTS public.experiments (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  name text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'ACTIVE',
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 4. experiment_variants
CREATE TABLE IF NOT EXISTS public.experiment_variants (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  experiment_id uuid NOT NULL REFERENCES public.experiments(id) ON DELETE CASCADE,
  name text NOT NULL,
  description text,
  allocation_percentage integer NOT NULL,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. experiment_assignments
CREATE TABLE IF NOT EXISTS public.experiment_assignments (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  experiment_id uuid NOT NULL REFERENCES public.experiments(id) ON DELETE CASCADE,
  variant_id uuid NOT NULL REFERENCES public.experiment_variants(id) ON DELETE CASCADE,
  customer_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  session_id text,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 6. experiment_events
CREATE TABLE IF NOT EXISTS public.experiment_events (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  assignment_id uuid NOT NULL REFERENCES public.experiment_assignments(id) ON DELETE CASCADE,
  event_type text NOT NULL, -- impression, conversion
  value numeric DEFAULT 0,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 7. experiment_metrics
CREATE TABLE IF NOT EXISTS public.experiment_metrics (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  experiment_id uuid NOT NULL REFERENCES public.experiments(id) ON DELETE CASCADE,
  variant_id uuid NOT NULL REFERENCES public.experiment_variants(id) ON DELETE CASCADE,
  impressions integer DEFAULT 0,
  conversions integer DEFAULT 0,
  conversion_rate numeric DEFAULT 0,
  aov numeric DEFAULT 0,
  revenue numeric DEFAULT 0,
  sample_size integer DEFAULT 0,
  recommendation text,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 8. ml_pipeline_runs
CREATE TABLE IF NOT EXISTS public.ml_pipeline_runs (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  run_name text NOT NULL,
  model_family text NOT NULL,
  model_version text NOT NULL,
  status text NOT NULL,
  started_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
  ended_at timestamp with time zone,
  duration_ms integer,
  input_row_count integer DEFAULT 0,
  output_row_count integer DEFAULT 0,
  error_count integer DEFAULT 0,
  warning_count integer DEFAULT 0,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 9. model_predictions
CREATE TABLE IF NOT EXISTS public.model_predictions (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  run_id uuid NOT NULL REFERENCES public.ml_pipeline_runs(id) ON DELETE CASCADE,
  entity_id uuid,
  entity_type text,
  prediction_value numeric,
  prediction_category text,
  confidence numeric,
  features jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 10. feature_snapshots
CREATE TABLE IF NOT EXISTS public.feature_snapshots (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  entity_id uuid,
  entity_type text,
  features jsonb NOT NULL,
  snapshot_date date NOT NULL DEFAULT CURRENT_DATE,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 11. model_monitoring_alerts
CREATE TABLE IF NOT EXISTS public.model_monitoring_alerts (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  run_id uuid REFERENCES public.ml_pipeline_runs(id) ON DELETE CASCADE,
  alert_type text NOT NULL,
  severity text NOT NULL,
  description text NOT NULL,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ==========================================
-- RLS POLICIES
-- ==========================================

-- Enable RLS
ALTER TABLE public.ops_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.experiment_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.experiment_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.experiment_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.experiment_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ml_pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feature_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_monitoring_alerts ENABLE ROW LEVEL SECURITY;

-- Admins can read and write everything
CREATE POLICY "Admin full access on ops_insights" ON public.ops_insights FOR ALL TO authenticated USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
);
CREATE POLICY "Admin full access on support_tickets" ON public.support_tickets FOR ALL TO authenticated USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
);
CREATE POLICY "Admin full access on experiments" ON public.experiments FOR ALL TO authenticated USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
);
CREATE POLICY "Admin full access on experiment_variants" ON public.experiment_variants FOR ALL TO authenticated USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
);
CREATE POLICY "Admin full access on experiment_assignments" ON public.experiment_assignments FOR ALL TO authenticated USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
);
CREATE POLICY "Admin full access on experiment_events" ON public.experiment_events FOR ALL TO authenticated USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
);
CREATE POLICY "Admin full access on experiment_metrics" ON public.experiment_metrics FOR ALL TO authenticated USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
);
CREATE POLICY "Admin full access on ml_pipeline_runs" ON public.ml_pipeline_runs FOR ALL TO authenticated USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
);
CREATE POLICY "Admin full access on model_predictions" ON public.model_predictions FOR ALL TO authenticated USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
);
CREATE POLICY "Admin full access on feature_snapshots" ON public.feature_snapshots FOR ALL TO authenticated USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
);
CREATE POLICY "Admin full access on model_monitoring_alerts" ON public.model_monitoring_alerts FOR ALL TO authenticated USING (
  EXISTS (SELECT 1 FROM public.profiles WHERE profiles.id = auth.uid() AND profiles.role = 'admin')
);

-- Customers
-- Can create and read own support_tickets
CREATE POLICY "Customer can read own support tickets" ON public.support_tickets FOR SELECT TO authenticated USING (customer_id = auth.uid());
CREATE POLICY "Customer can create own support tickets" ON public.support_tickets FOR INSERT TO authenticated WITH CHECK (customer_id = auth.uid());

-- Customers can create and read their own assignments
CREATE POLICY "Customer can read own experiment assignments" ON public.experiment_assignments FOR SELECT TO authenticated USING (customer_id = auth.uid());
CREATE POLICY "Customer can insert own experiment assignments" ON public.experiment_assignments FOR INSERT TO authenticated WITH CHECK (customer_id = auth.uid());

-- Customers can create events for their assignments
CREATE POLICY "Customer can create experiment events" ON public.experiment_events FOR INSERT TO authenticated WITH CHECK (
  EXISTS (SELECT 1 FROM public.experiment_assignments WHERE experiment_assignments.id = assignment_id AND experiment_assignments.customer_id = auth.uid())
);

-- Everyone can read experiments and variants for assignment logic (or anonymous / authenticated)
CREATE POLICY "Public read experiments" ON public.experiments FOR SELECT USING (true);
CREATE POLICY "Public read experiment_variants" ON public.experiment_variants FOR SELECT USING (true);

-- Merchant and Partner can read own insights
CREATE POLICY "Merchant/Partner can read own ops insights" ON public.ops_insights FOR SELECT TO authenticated USING (entity_id = auth.uid());


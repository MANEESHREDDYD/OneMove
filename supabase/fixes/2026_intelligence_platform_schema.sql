-- Intelligence Platform Core Schema (Phase 1)
-- Creates Data Engineering and Metric Store tables

-- 1. Data Pipeline Runs
CREATE TABLE IF NOT EXISTS public.data_pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    start_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    end_time TIMESTAMPTZ,
    rows_processed INTEGER DEFAULT 0,
    error_message TEXT
);

ALTER TABLE public.data_pipeline_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_all_pipeline_runs" ON public.data_pipeline_runs FOR ALL USING (is_admin());

-- 2. Data Quality Results
CREATE TABLE IF NOT EXISTS public.data_quality_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES public.data_pipeline_runs(id) ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pass', 'fail', 'warning')),
    failed_rows_count INTEGER DEFAULT 0,
    sample_failed_records JSONB,
    severity TEXT CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    affected_table TEXT,
    recommended_fix TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.data_quality_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_all_dq_results" ON public.data_quality_results FOR ALL USING (is_admin());

-- 3. Daily Marketplace Metrics
CREATE TABLE IF NOT EXISTS public.daily_marketplace_metrics (
    date DATE PRIMARY KEY,
    gmv NUMERIC(10, 2) DEFAULT 0,
    net_revenue NUMERIC(10, 2) DEFAULT 0,
    total_orders INTEGER DEFAULT 0,
    completed_orders INTEGER DEFAULT 0,
    cancelled_orders INTEGER DEFAULT 0,
    refund_rate NUMERIC(5, 2) DEFAULT 0,
    active_customers INTEGER DEFAULT 0,
    active_partners INTEGER DEFAULT 0,
    active_merchants INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.daily_marketplace_metrics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_all_daily_metrics" ON public.daily_marketplace_metrics FOR ALL USING (is_admin());

-- 4. Merchant Daily Metrics
CREATE TABLE IF NOT EXISTS public.merchant_daily_metrics (
    date DATE NOT NULL,
    merchant_id UUID REFERENCES public.merchants(id) ON DELETE CASCADE,
    gmv NUMERIC(10, 2) DEFAULT 0,
    total_orders INTEGER DEFAULT 0,
    completed_orders INTEGER DEFAULT 0,
    cancelled_orders INTEGER DEFAULT 0,
    acceptance_rate NUMERIC(5, 2) DEFAULT 0,
    avg_prep_time_minutes NUMERIC(5, 2) DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (date, merchant_id)
);

ALTER TABLE public.merchant_daily_metrics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_all_merchant_metrics" ON public.merchant_daily_metrics FOR ALL USING (is_admin());

-- 5. Partner Daily Metrics
CREATE TABLE IF NOT EXISTS public.partner_daily_metrics (
    date DATE NOT NULL,
    partner_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    completed_jobs INTEGER DEFAULT 0,
    earnings NUMERIC(10, 2) DEFAULT 0,
    online_hours NUMERIC(5, 2) DEFAULT 0,
    acceptance_rate NUMERIC(5, 2) DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (date, partner_id)
);

ALTER TABLE public.partner_daily_metrics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_all_partner_metrics" ON public.partner_daily_metrics FOR ALL USING (is_admin());

-- 6. Customer Daily Metrics
CREATE TABLE IF NOT EXISTS public.customer_daily_metrics (
    date DATE NOT NULL,
    customer_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    orders_placed INTEGER DEFAULT 0,
    spend NUMERIC(10, 2) DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (date, customer_id)
);

ALTER TABLE public.customer_daily_metrics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_all_customer_metrics" ON public.customer_daily_metrics FOR ALL USING (is_admin());

-- 7. Service Type Daily Metrics
CREATE TABLE IF NOT EXISTS public.service_type_daily_metrics (
    date DATE NOT NULL,
    service_type public.service_type NOT NULL,
    gmv NUMERIC(10, 2) DEFAULT 0,
    total_orders INTEGER DEFAULT 0,
    completed_orders INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (date, service_type)
);

ALTER TABLE public.service_type_daily_metrics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_all_service_type_metrics" ON public.service_type_daily_metrics FOR ALL USING (is_admin());

-- 8. Metric Snapshots (Generic)
CREATE TABLE IF NOT EXISTS public.metric_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name TEXT NOT NULL,
    metric_value NUMERIC NOT NULL,
    dimensions JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_metric_snapshots_name ON public.metric_snapshots(metric_name);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_timestamp ON public.metric_snapshots(timestamp);

ALTER TABLE public.metric_snapshots ENABLE ROW LEVEL SECURITY;
CREATE POLICY "admin_all_metric_snapshots" ON public.metric_snapshots FOR ALL USING (is_admin());

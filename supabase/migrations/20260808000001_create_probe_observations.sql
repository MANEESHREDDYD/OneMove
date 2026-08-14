-- 20260808000001_create_probe_observations.sql
-- Create the dedicated probe_observations table for Anchor and Stress Burst panels

CREATE TABLE IF NOT EXISTS public.probe_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    study_id UUID NOT NULL,
    assignment_id UUID NOT NULL,
    participant_id UUID NOT NULL REFERENCES auth.users(id),
    client_event_id UUID NOT NULL,
    zone_cluster TEXT NOT NULL,
    h3_r8 TEXT,
    platform TEXT NOT NULL,
    intent TEXT NOT NULL,
    protocol TEXT NOT NULL,
    scheduled_for TIMESTAMPTZ,
    observed_at_device TIMESTAMPTZ NOT NULL,
    received_at_server TIMESTAMPTZ NOT NULL DEFAULT now(),
    device_clock_offset_ms BIGINT,
    time_quality TEXT,
    timing_deviation_seconds BIGINT,
    timing_valid BOOLEAN,
    eta_low_min INTEGER,
    eta_high_min INTEGER,
    option_count INTEGER,
    availability_state TEXT NOT NULL,
    reference_basket_price NUMERIC,
    protocol_version TEXT NOT NULL,
    provenance TEXT NOT NULL DEFAULT 'OBSERVED',
    supersedes_id UUID REFERENCES public.probe_observations(id),
    correction_reason TEXT,
    record_status TEXT NOT NULL DEFAULT 'ACTIVE',
    client_payload_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Constraints
    CONSTRAINT chk_eta_low_min CHECK (eta_low_min >= 0),
    CONSTRAINT chk_eta_high_min CHECK (eta_high_min >= eta_low_min),
    CONSTRAINT chk_option_count CHECK (option_count >= 0),
    CONSTRAINT chk_ref_basket CHECK (reference_basket_price >= 0 OR reference_basket_price IS NULL),
    CONSTRAINT chk_protocol CHECK (protocol IN ('ANCHOR', 'BURST')),
    CONSTRAINT chk_availability CHECK (availability_state IN ('IN_STOCK', 'LIMITED', 'OUT_OF_STOCK', 'NOT_SHOWN', 'UNKNOWN')),
    CONSTRAINT chk_record_status CHECK (record_status IN ('ACTIVE', 'SUPERSEDED', 'WITHDRAWN')),

    -- Participant scoped idempotency
    CONSTRAINT uq_probe_participant_client_event UNIQUE (participant_id, client_event_id)
);

-- Indexes for anticipated study queries
CREATE INDEX IF NOT EXISTS idx_probe_obs_study_time ON public.probe_observations(study_id, received_at_server);
CREATE INDEX IF NOT EXISTS idx_probe_obs_participant_time ON public.probe_observations(participant_id, received_at_server);
CREATE INDEX IF NOT EXISTS idx_probe_obs_zone_time ON public.probe_observations(zone_cluster, received_at_server);
CREATE INDEX IF NOT EXISTS idx_probe_obs_platform_zone_time ON public.probe_observations(platform, zone_cluster, received_at_server);
CREATE INDEX IF NOT EXISTS idx_probe_obs_assignment ON public.probe_observations(assignment_id);

-- RLS
ALTER TABLE public.probe_observations ENABLE ROW LEVEL SECURITY;

-- Participant may insert their own probe observations
CREATE POLICY "Participant can insert own probe observations"
    ON public.probe_observations
    FOR INSERT
    WITH CHECK (auth.uid() = participant_id);

-- Participant may select their own probe observations
CREATE POLICY "Participant can select own probe observations"
    ON public.probe_observations
    FOR SELECT
    USING (auth.uid() = participant_id);
    
-- Note: Update and Delete are deliberately omitted (append-only)
-- Owner QC is assumed to use the service role or a specific admin policy if configured,
-- but for this scope, service role is sufficient for ETL/QC.

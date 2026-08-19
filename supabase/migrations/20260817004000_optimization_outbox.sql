-- Optimization Transactional Outbox
CREATE TABLE IF NOT EXISTS public.optimization_outbox (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_id UUID NOT NULL,
    workspace_id TEXT NOT NULL,
    event_type TEXT NOT NULL DEFAULT 'OPTIMIZATION_SUBMITTED',
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ,
    pubsub_message_id TEXT,
    attempts INT NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_error TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING'
);

CREATE INDEX IF NOT EXISTS idx_optimization_outbox_pending ON public.optimization_outbox (status, next_attempt_at) WHERE status = 'PENDING';
CREATE INDEX IF NOT EXISTS idx_optimization_outbox_aggregate ON public.optimization_outbox (aggregate_id);

ALTER TABLE public.optimization_outbox ENABLE ROW LEVEL SECURITY;

CREATE POLICY "optimization_outbox_workspace_isolation"
    ON public.optimization_outbox
    FOR ALL
    USING (
        workspace_id IN (
            SELECT workspace_id::text
            FROM public.workspace_members
            WHERE user_id = auth.uid()
        )
    );

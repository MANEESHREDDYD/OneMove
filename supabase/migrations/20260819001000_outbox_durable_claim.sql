-- AUDIT-3: Durable outbox claim protocol with leases and fencing tokens.
--
-- Before this migration claim_pending_outbox_events() ran
--   SELECT ... FOR UPDATE SKIP LOCKED
-- inside a `with self._connect()` block, which COMMITS and CLOSES the connection
-- on exit. Every row lock was therefore released before the Pub/Sub publish ran
-- and the rows stayed status='PENDING'. With max_instance_count=2 both
-- dispatchers selected and published the same events.
--
-- The fix is a two-phase protocol:
--   1. claim  : one transaction moves rows PENDING -> CLAIMED, stamping
--                lease_owner / lease_expires_at / fencing_token, then commits.
--   2. finalize: PUBLISHED/FAILED/DEAD transitions are gated on
--                (status='CLAIMED' AND fencing_token = :token AND lease_owner = :owner)
--                so a dispatcher whose lease already expired and was stolen can
--                never mutate the row (zero rows updated == LOST_LEASE).
--
-- Idempotent / re-appliable: every statement is IF NOT EXISTS guarded and no
-- existing column is dropped or renamed.

-- ---------------------------------------------------------------------------
-- Columns
-- ---------------------------------------------------------------------------
ALTER TABLE public.optimization_outbox
    ADD COLUMN IF NOT EXISTS lease_owner TEXT;

ALTER TABLE public.optimization_outbox
    ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ;

ALTER TABLE public.optimization_outbox
    ADD COLUMN IF NOT EXISTS fencing_token UUID;

ALTER TABLE public.optimization_outbox
    ADD COLUMN IF NOT EXISTS max_attempts INT NOT NULL DEFAULT 5;

ALTER TABLE public.optimization_outbox
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- Canonical delivery counter. The legacy `attempts` column is preserved (never
-- dropped) and is kept in lockstep by the application writes so any existing
-- reader/monitoring query against `attempts` keeps working.
ALTER TABLE public.optimization_outbox
    ADD COLUMN IF NOT EXISTS attempt_count INT NOT NULL DEFAULT 0;

UPDATE public.optimization_outbox
SET attempt_count = attempts
WHERE attempt_count = 0
  AND attempts > 0;

-- ---------------------------------------------------------------------------
-- Status domain
-- ---------------------------------------------------------------------------
-- Normalize any legacy terminal rows before constraining the domain: rows that
-- exhausted their retries belong in the dead-letter state, not 'FAILED'.
UPDATE public.optimization_outbox
SET status = 'DEAD',
    updated_at = now()
WHERE status = 'FAILED'
  AND attempt_count >= max_attempts;

UPDATE public.optimization_outbox
SET status = 'PENDING',
    updated_at = now()
WHERE status NOT IN ('PENDING', 'CLAIMED', 'PUBLISHED', 'FAILED', 'DEAD');

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_optimization_outbox_status'
          AND conrelid = 'public.optimization_outbox'::regclass
    ) THEN
        ALTER TABLE public.optimization_outbox
            ADD CONSTRAINT chk_optimization_outbox_status
            CHECK (status IN ('PENDING', 'CLAIMED', 'PUBLISHED', 'FAILED', 'DEAD'));
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_optimization_outbox_max_attempts'
          AND conrelid = 'public.optimization_outbox'::regclass
    ) THEN
        ALTER TABLE public.optimization_outbox
            ADD CONSTRAINT chk_optimization_outbox_max_attempts
            CHECK (max_attempts > 0);
    END IF;
END
$$;

-- ---------------------------------------------------------------------------
-- Indexes supporting the claim query
-- ---------------------------------------------------------------------------
-- Drives the PENDING arm: WHERE status='PENDING' AND next_attempt_at <= now()
--                          ORDER BY created_at
CREATE INDEX IF NOT EXISTS idx_optimization_outbox_claim_pending
    ON public.optimization_outbox (next_attempt_at, created_at)
    WHERE status = 'PENDING';

-- Drives the reclaim arm: WHERE status='CLAIMED' AND lease_expires_at < now()
CREATE INDEX IF NOT EXISTS idx_optimization_outbox_claim_expired
    ON public.optimization_outbox (lease_expires_at, created_at)
    WHERE status = 'CLAIMED';

-- Operational lookup for dead-lettered events.
CREATE INDEX IF NOT EXISTS idx_optimization_outbox_dead
    ON public.optimization_outbox (created_at)
    WHERE status = 'DEAD';

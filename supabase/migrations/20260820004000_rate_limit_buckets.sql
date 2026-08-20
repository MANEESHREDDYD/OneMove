-- 20260820004000_rate_limit_buckets.sql
-- F-023: move rate limiting out of one API process and into the database.
--
-- WHY THIS EXISTS
--   The limiter was a per-process dict (services/api/core/telemetry.py).
--   The API runs at max_instance_count = 10 (infra/gcp/modules/cloud_run/main.tf:79),
--   so every configured quota was silently multiplied by the number of live
--   instances, and the window dict was never pruned -- an unbounded map keyed by
--   a caller-supplied principal, i.e. a remote memory-exhaustion vector.
--
-- WHY POSTGRES AND NOT A NEW SERVICE
--   Postgres is already a hard dependency of this API. `INSERT ... ON CONFLICT
--   DO UPDATE ... RETURNING` is a single atomic statement: it takes a row lock,
--   increments, and hands back the post-increment value in one round trip. That
--   is exactly the primitive a distributed counter needs. Adding Redis would add
--   a second stateful dependency, a second failure mode, and a second thing to
--   secure, to buy a property Postgres already has.
--
-- COUNTER SEMANTICS
--   Fixed window. The window boundary is computed from the DATABASE clock, never
--   from an application clock, so ten API instances with skewed clocks still
--   agree on which bucket a request belongs to.

-- ---------------------------------------------------------------------------
-- 1. Deterministic window boundary.
--
--    floor(epoch / width) * width. IMMUTABLE so it can be used in an index or a
--    generated column later; callers pass now() in explicitly rather than the
--    function reading it, which is what keeps it immutable and testable.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.rate_limit_window_start(
    p_now            TIMESTAMPTZ,
    p_window_seconds INTEGER
)
RETURNS TIMESTAMPTZ
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
    SELECT to_timestamp(
        floor(extract(epoch FROM p_now) / GREATEST(p_window_seconds, 1))
        * GREATEST(p_window_seconds, 1)
    )
$$;

-- ---------------------------------------------------------------------------
-- 2. The bucket table.
--
--    The primary key IS the rate-limit key: (workspace_id, user_id,
--    endpoint_class, window_start). Four dimensions, no surrogate id -- a
--    surrogate would let the same logical bucket exist twice and quietly double
--    the quota, which is the exact bug being fixed.
--
--    Window WIDTH is deliberately not part of the key. Width is a total function
--    of endpoint_class (see RATE_LIMIT_POLICIES in services/api/core/ratelimit.py),
--    so a class can never be evaluated against two widths at once and two
--    different budgets can never collide on one row.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.rate_limit_buckets (
    -- '-' is the sentinel for "no workspace selected" (pre-auth traffic).
    -- Never NULL: NULL would make the primary key non-unique for anonymous
    -- callers and silently disable the limit for exactly the traffic that needs
    -- it most.
    workspace_id   TEXT        NOT NULL,

    -- Either a subject id, or an 'ip:<hash>' network sentinel. See the module
    -- docstring in ratelimit.py for why the network bucket is the enforceable
    -- one and the subject bucket is the fairness one.
    user_id        TEXT        NOT NULL,

    endpoint_class TEXT        NOT NULL,
    window_start   TIMESTAMPTZ NOT NULL,

    request_count  INTEGER     NOT NULL DEFAULT 0,
    expires_at     TIMESTAMPTZ NOT NULL,

    PRIMARY KEY (workspace_id, user_id, endpoint_class, window_start),

    CONSTRAINT chk_rate_limit_endpoint_class CHECK (endpoint_class IN (
        -- The six endpoint classes.
        'AUTH',
        'READ',
        'WRITE',
        'OPTIMIZATION',
        'ASSISTANT',
        'ADMIN',
        -- Extra long-window quota buckets. These are budgets, not endpoint
        -- classes; they share the table because they share the key shape.
        'ASSISTANT_DAILY',
        'ASSISTANT_TOOL_DAILY'
    )),

    -- A negative or absurd count means an increment path was rewritten wrongly.
    -- Fail the write rather than under-enforce.
    CONSTRAINT chk_rate_limit_count_sane CHECK (request_count >= 0),

    -- expires_at must genuinely be in the future of its window, otherwise a row
    -- could be inserted pre-expired and the prune would delete live buckets.
    CONSTRAINT chk_rate_limit_expiry_after_window CHECK (expires_at > window_start)
);

-- ---------------------------------------------------------------------------
-- 3. Bounded storage.
--
--    PROOF THAT THIS TABLE CANNOT GROW WITHOUT LIMIT
--
--    (a) Bounded key space per window. window_start only ever takes values on a
--        window boundary, and endpoint_class is constrained to eight values. So
--        rows in any one window <= (distinct workspace_id x user_id pairs) x 8.
--
--    (b) Bounded distinct identities. user_id is not free text in practice: an
--        unauthenticated caller can only ever produce 'ip:<hash>', one value per
--        source address. A caller who presents a bearer token could otherwise
--        mint identities at will, so the application checks the NETWORK bucket
--        for every request and stops issuing database writes for a source
--        address once that bucket is exhausted (ratelimit.py: the deny cache).
--        Rows creatable per source address per window are therefore bounded by
--        that address's own request budget.
--
--    (c) Bounded retention. Every row carries expires_at, and prune_rate_limit_buckets()
--        removes rows whose window has closed. Steady state is at most two
--        windows of live keys: the current one and the one being pruned.
--
--    (a) and (b) bound the width, (c) bounds the depth. Neither depends on a
--        caller behaving well.
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_rate_limit_buckets_expires_at
    ON public.rate_limit_buckets (expires_at);

-- Bounded-batch prune. The batch cap matters: an unbounded DELETE on a hot
-- table takes a long lock and can itself become the outage. Returns the number
-- of rows actually removed so the caller can tell "nothing to do" from
-- "hit the cap, run me again".
CREATE OR REPLACE FUNCTION public.prune_rate_limit_buckets(
    p_now        TIMESTAMPTZ DEFAULT now(),
    p_batch_size INTEGER     DEFAULT 5000
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    WITH doomed AS (
        SELECT ctid
        FROM public.rate_limit_buckets
        WHERE expires_at <= p_now
        ORDER BY expires_at
        LIMIT GREATEST(p_batch_size, 1)
        FOR UPDATE SKIP LOCKED
    )
    DELETE FROM public.rate_limit_buckets b
    USING doomed
    WHERE b.ctid = doomed.ctid;

    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;
$$;

COMMENT ON FUNCTION public.prune_rate_limit_buckets(TIMESTAMPTZ, INTEGER) IS
    'Deletes expired rate-limit buckets in a bounded batch. Called opportunistically '
    'by the API on each window rollover; safe to also schedule externally. '
    'SKIP LOCKED means concurrent pruners divide the work instead of blocking.';

-- ---------------------------------------------------------------------------
-- 4. Privileges.
--
--    This table is API infrastructure. Nothing reachable through PostgREST has
--    any business reading it: the counts reveal who is calling what and how
--    often, across tenants. RLS is enabled with NO policies, which denies every
--    non-owner role outright, and the grants are revoked so the denial does not
--    depend on RLS alone.
-- ---------------------------------------------------------------------------
ALTER TABLE public.rate_limit_buckets ENABLE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON public.rate_limit_buckets FROM anon, authenticated;
REVOKE ALL PRIVILEGES ON FUNCTION public.prune_rate_limit_buckets(TIMESTAMPTZ, INTEGER)
    FROM anon, authenticated;

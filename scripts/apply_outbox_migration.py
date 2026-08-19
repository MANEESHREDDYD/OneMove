import sys

import psycopg

from services.common.db_dsn import get_database_dsn


def main():
    dsn = get_database_dsn()
    if not dsn:
        print("No DB DSN found, skipping DB migration.")
        return 0
    print("Applying optimization_outbox schema to DB...")
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("""
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
            """)
            conn.commit()
    print("optimization_outbox table ready!")
    return 0


if __name__ == "__main__":
    sys.exit(main())

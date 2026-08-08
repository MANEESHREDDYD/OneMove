-- Add idempotent retry columns for client-side offline outboxes
ALTER TABLE IF EXISTS public.volunteer_order_events
ADD COLUMN IF NOT EXISTS client_event_id TEXT UNIQUE;

ALTER TABLE IF EXISTS public.assignments
ADD COLUMN IF NOT EXISTS client_assignment_id TEXT UNIQUE;
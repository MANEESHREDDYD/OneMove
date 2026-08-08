-- Add payload JSONB to volunteer_order_events as a forward migration
ALTER TABLE volunteer_order_events ADD COLUMN payload JSONB;

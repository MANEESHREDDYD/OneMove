-- Fix INTEGER overflow on legacy travel demand columns
-- The units for expected_travel_seconds and p95_travel_seconds are actually demand_units * seconds
-- which can easily exceed the 32-bit integer limit (2.14B) in large scenarios.

ALTER TABLE public.decision_records
    ALTER COLUMN expected_travel_seconds TYPE BIGINT,
    ALTER COLUMN p95_travel_seconds TYPE BIGINT;

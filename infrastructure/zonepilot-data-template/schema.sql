-- Subagent D: Database Schema Setup
CREATE SCHEMA IF NOT EXISTS zonepilot_ops;

-- Enum for status
CREATE TYPE zonepilot_ops.run_status AS ENUM ('RUNNING', 'SUCCESS', 'FAILED', 'PARTIAL', 'INTEGRITY_FAILED');

CREATE TABLE IF NOT EXISTS zonepilot_ops.collection_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider VARCHAR(255) NOT NULL,
    dataset VARCHAR(255) NOT NULL,
    logical_interval VARCHAR(255) NOT NULL,
    query_hash VARCHAR(64) NOT NULL,
    status zonepilot_ops.run_status NOT NULL,
    runner_id VARCHAR(255) NOT NULL,
    claimed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    lease_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    result_metadata JSONB,
    
    -- Enforce uniqueness of the logical slot
    CONSTRAINT uq_logical_slot UNIQUE (provider, dataset, logical_interval, query_hash),
    
    -- Ensure lease is properly set when running
    CONSTRAINT chk_running_lease CHECK (status != 'RUNNING' OR lease_expires_at IS NOT NULL)
);

-- Grant privileges for the collector role
-- Run this block when zonepilot_collector role exists
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'zonepilot_collector') THEN
    GRANT USAGE ON SCHEMA zonepilot_ops TO zonepilot_collector;
    GRANT SELECT, INSERT, UPDATE ON zonepilot_ops.collection_runs TO zonepilot_collector;
    -- Ensure least privilege: no DROP, TRUNCATE, DELETE, or CREATE schema
  END IF;
END
$$;

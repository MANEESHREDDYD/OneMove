-- Migration: Create zonepilot_collector least privilege role

-- 1. Create Role
CREATE ROLE zonepilot_collector WITH
  LOGIN
  NOSUPERUSER
  NOCREATEDB
  NOCREATEROLE
  NOREPLICATION
  NOBYPASSRLS
  CONNECTION LIMIT 10;

-- Note: The password MUST be set externally by the owner.
-- Do NOT set or commit the password here.
-- Example: ALTER ROLE zonepilot_collector WITH PASSWORD 'REPLACE_ME_SECURELY';

-- 2. Create Schema for Ops Control Plane
CREATE SCHEMA IF NOT EXISTS zonepilot_ops;

-- 3. Grant Minimum Privileges
GRANT USAGE ON SCHEMA zonepilot_ops TO zonepilot_collector;

-- Assuming tables will be created in this schema, grant privileges on all current and future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA zonepilot_ops GRANT SELECT, INSERT, UPDATE ON TABLES TO zonepilot_collector;

-- Explicitly revoke access to other schemas just in case
REVOKE ALL PRIVILEGES ON SCHEMA auth FROM zonepilot_collector;
REVOKE ALL PRIVILEGES ON SCHEMA public FROM zonepilot_collector;

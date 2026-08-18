# ZonePilot Security Architecture & Policy

## 1. Authentication & Authorization
- **JWT Verification:** Supabase Auth JWT tokens verified using asymmetric ES256/RS256 keys from JWKS, with fallback to HMAC-SHA256 secret.
- **Tenancy Boundary:** Server-side `WorkspacePrincipal` resolution prevents header spoofing and privilege escalation.
- **Role-Based Access Control:** Strict role hierarchy (`OWNER`, `ADMIN`, `RESEARCHER`, `VIEWER`, `INTEGRATION_USER`, `COLLECTOR`).

## 2. Row Level Security (RLS)
- All tables in PostgreSQL are protected with Row Level Security.
- Cross-workspace queries fail closed and return zero rows or HTTP 403.

## 3. Cryptographic Storage & Secrets Protection
- Storage buckets (`zonepilot-raw-data`, `zonepilot-evidence`) are private with HMAC authentication.
- Zero secret values are exposed in log messages, telemetry traces, or client error envelopes.

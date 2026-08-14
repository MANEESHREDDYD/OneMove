# Milestone A - Architecture Realization

## Implementation Delta Map (OneMove -> ZonePilot)

- **Architecture Boundary**: Currently a monolithic Next.js app in `/app`. Moving to `apps/observatory` (PWA) and `services/api` (FastAPI).
- **Data Provenance**: Currently heavily `SYNTHETIC` and `DETERMINISTIC_SEED`. Must be isolated into `legacy_demo` and replaced with strict `OBSERVED`/`DERIVED`/`SIMULATED` lineage.
- **Database Schema**: Currently uses `schema.sql` with no indexes and permissive RLS. Must be replaced with ordered immutable migrations, strict RLS for human sessions, and explicit `studies` + `volunteer_orders` tables.
- **Auth Model**: Currently allows broad public registration with self-assigned roles. Must be locked to invite-only with verified JWTs and isolated service clients.

## Phase-0 Implementation Order (FR-1 to FR-6)

1. **FR-1**: Provenance + quarantine (Quarantine legacy mock logic)
2. **FR-2**: Security/auth foundation (Fix RLS, lock down auth)
3. **FR-3**: Canonical migrations (Create immutable schema chain)
4. **FR-4**: Operational telemetry (Append-only events, provenance stamping)
5. **FR-4b**: Governance mechanics (Snapshot, export, withdrawal logic)
6. **FR-5**: Service and PWA skeleton (FastAPI backend and Next.js PWA structure)
7. **FR-6**: Foundation verification (Final checkpoint before data collection)

## Identified Owner Blockers
- **Docker/Supabase Unavailability**: The local Docker Desktop environment is not running, and thus the local Supabase instance cannot be started or interacted with (`dockerDesktopLinuxEngine` connection failure). This blocks FR-2 and FR-3 which require database access to apply and verify RLS and migrations.
- **Remote Supabase Credentials**: If local Docker cannot be used, remote Supabase staging credentials are required to execute database-dependent steps.

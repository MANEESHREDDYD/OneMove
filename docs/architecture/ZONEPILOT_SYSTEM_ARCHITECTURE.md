# ZonePilot System Architecture

## 1. Context Architecture & Trust Boundaries
ZonePilot separates operational telemetry collection, machine harvesting, and research data processing into clear trust tiers:

- **Human Field Telemetry (OBSERVER / VOLUNTEER)**: Authenticated via Supabase Auth (JWT). Interacts via Next.js Observatory client. Client operations write to local IndexedDB outbox (`PENDING_LOCAL`), flushing over HTTP to FastAPI (`/v1/probes`, `/v1/events`). DB mutations are governed by Postgres Row Level Security (RLS).
- **Machine Ingestion & Automated Collectors**: Operates via backend service identities (`SUPABASE_SERVICE_ROLE_KEY`). Executes scheduled point-in-time fetches (Open-Meteo weather, OSRM routing, spatial indexing). Output is persisted to `$ZONEPILOT_DATA_ROOT/private/raw/`.
- **Private Research & Analytical Processing**: Inaccessible from external API boundaries. Pulls immutable raw snapshots, executes Bronze normalization, Silver feature alignment, and DQ validation. Produces Experiment A & B datasets.

## 2. Logical Data Architecture
```
[ Human Observer / Volunteer ]
              │
    (JWT Authenticated)
              ▼
    [ Next.js Observatory ] ──(Offline Outbox)──► [ FastAPI Boundary ]
              │                                        │
              ▼                                        ▼
    [ Supabase Auth ]                           [ Supabase Postgres ]
                                                       │
                                              (Postgres RLS Policies)
                                                       │
                                                       ▼
                                            [ probe_observations ]
                                                       │
                                            (ETL Private Ingestion)
                                                       ▼
[ Scheduled Machine Collectors ] ────────► [ $ZONEPILOT_DATA_ROOT ]
  - Open-Meteo Weather                       ├── private/raw/
  - OSRM Bengaluru Routing                   ├── private/bronze/
  - Daily Scheduler (00:00/00:05 IST)        └── private/silver/
                                                       │
                                             (Fail-Closed Phase Filter)
                                                       ▼
                                           [ Experiment A Gold Dataset ]
```

## 3. Storage & Separation Boundaries
- **Operational Database**: Supabase Postgres for auth, active assignments, probe observations lineage, and volunteer order events.
- **Private Local Research Plane**: `$ZONEPILOT_DATA_ROOT/private/` outside version control for physical Parquet snapshots and manifests.
- **Evidence Lineage**: Observations retain immutable provenance flags (`OBSERVED`, `FIXTURE`, `SIMULATED`, `DERIVED`). Observations tagged with `study_phase = DRY_RUN` are strictly excluded from Experiment A dataset boundaries.

# ZonePilot Canonical Component Map

| Component Area | Canonical Path | Owner | Input | Output | Data Classification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Authentication** | `services/api/core/auth.py` | API & Security | Bearer JWT Header | Verified Claims / `sub` | `CONFIDENTIAL_INTERNAL` |
| **Probe Ingestion** | `services/api/routers/events.py` | API Boundary | `ProbeObservationCreate` | Postgres `probe_observations` | `OBSERVED_TELEMETRY` |
| **ETL Pipeline** | `services/etl/pipeline.py` | Data Engineering | PostgREST / Postgres | `raw`, `bronze`, `silver` Parquet | `RESEARCH_SNAPSHOT` |
| **Open-Meteo Collector** | `services/collectors/openmeteo_real.py` | Machine Collectors | Open-Meteo REST API | `private/raw/observed/*.parquet` | `PUBLIC_ENVIRONMENTAL` |
| **Routing Engine** | `services/routing/osrm_pipeline.py` | Geospatial | OSM PBF / Overpass XML | OSRM Distance & Duration Matrix | `PUBLIC_GEOSPATIAL` |
| **Scheduler** | `services/api/scheduler.py` | Orchestration | Cron / System Time (IST) | Daily Run Registry Manifests | `OPERATIONAL_METADATA` |
| **Backup / Restore** | `services/etl/backup_restore.py` | SRE / Infrastructure | Operational DB / Parquet | JSON Snapshot & Verification | `SYSTEM_BACKUP` |
| **Observatory Client** | `apps/observatory/` | Frontend | User Touch / Form Inputs | IndexedDB Outbox / API | `CLIENT_STATE` |

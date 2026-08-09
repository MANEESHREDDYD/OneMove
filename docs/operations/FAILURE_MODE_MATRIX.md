# ZonePilot Operations Failure Mode Matrix

| Failure Mode | Detection Mechanism | System / User Impact | Mitigation / Recovery Procedure | Severity |
| :--- | :--- | :--- | :--- | :--- |
| **Supabase DB Unreachable** | API health check failure (`/readyz` 503) | Client queues observations locally in IndexedDB outbox | Automatic outbox retry upon network restoration | `P1` |
| **JWT Key / Token Expiration** | `verify_token` raises 401 `Token expired` | API rejects observation request | Client outbox marks `AUTH_REQUIRED`, prompts user re-auth | `P2` |
| **Duplicate Transport Replay** | Unique constraint violation on `(participant_id, client_event_id)` | Duplicate HTTP POST received | Idempotent response returned; physical database retains 1 row | `P3` |
| **Open-Meteo API Timeout** | Open-Meteo collector exception logged | Environmental weather gap for historical hour | Collector retries with exponential backoff; manifest records missing timestamps | `P2` |
| **OSRM Docker Container Offline** | Connection refusal on `localhost:5000` | Routing engine falls back to haversine estimation | Engine returns `status: BLOCKED_BY_ENVIRONMENT` with haversine fallback | `P3` |
| **DRY_RUN Data Contamination** | `build_experiment_a_dataset` fail-closed check | Experiment A dataset generation aborted | Pipeline throws `ValueError` halting Gold dataset build | `P0` |

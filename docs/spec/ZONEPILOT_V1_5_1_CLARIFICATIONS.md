# ZonePilot v1.5.1 Clarifications

This document preserves the ZonePilot v1.5 spec and resolves specific implementation contradictions.

## C1 — Volunteer orders become append-only/event-oriented
Do not UPDATE the initial volunteer order merely to close it. Use `volunteer_orders` for the initial checkout observation. Add `volunteer_order_events` with event types such as DELIVERED, CANCELLED, REFUND_REQUESTED, REFUNDED, CORRECTION. `POST /v1/orders/{id}/close` must INSERT the closing event. Create a derived current-state view such as `volunteer_orders_current` for analytical convenience. Original observations remain immutable.

## C2 — Immutable correction mechanism
Add the required revision fields instead of referencing nonexistent fields. For applicable observational records support: `supersedes_id`, `correction_reason`, `record_status` (ACTIVE, SUPERSEDED, WITHDRAWN). Never silently edit research observations.

## C3 — Separate cloud operational plane from private research plane
Final boundary:
**CLOUD OPERATIONAL PLANE:** Observatory PWA → FastAPI → Supabase Postgres. Railway cron collectors → Supabase environmental tables. Where raw provider responses may legally be stored: → private Supabase Storage bucket.
**PRIVATE RESEARCH PLANE:** Supabase → `zonepilot snapshot-pull` → `$ZONEPILOT_DATA_ROOT/private/...` → bronze → silver → gold → models/twin/evaluation.
Railway performs collection and operational checks. The owner's private research environment performs snapshot pull, bronze, silver, gold, training, simulation, optimization, final evaluation, reproduce-final.

## C4 — Human sessions always use RLS
Interactive browser/owner actions use `get_user_db(jwt)` and remain subject to RLS. The secret client `get_service_db()` is for trusted non-interactive machine jobs only (collectors, merchant importer, snapshot export, withdrawal/retention processor, migrations, controlled service operations). Never switch an owner UI request into secret-key god mode merely because the user is owner. Principle: human session → user JWT + RLS; machine job → secret client.

## C5 — Fix data-duration gates
Experiment A requires enough chronology for train/calibration/holdout. Use: 12 usable study days minimum; 14 days target; minimum 3 full final holdout days; minimum 2 calibration days; remaining earlier days training. Do not hard-code calendar indexes in code. Derive temporal partitions from the frozen experiment protocol. Merchant operational study: ≥12 usable operational days minimum for strong held-out twin/policy claims; 14 days target; ≥300 valid orders target. If data is smaller, downgrade allowed claims rather than silently weakening evaluation.

## C6 — Participant roles
Do not make observer/volunteer/owner mutually exclusive if a participant performs multiple activities. Prefer normalized `participant_roles(participant_id, role)` with roles such as OBSERVER, VOLUNTEER, OWNER.

## C7 — HMAC identifiers
Use keyed HMAC rather than plain hashes for merchant external identifiers. Apply where needed to: rider external IDs, order external IDs, source event identifiers. Store `hash_key_version` but never store the hashing secret.

## C8 — Normalize event actors
Do not store uncontrolled actor text. Use enum: CUSTOMER, MERCHANT, RIDER, SYSTEM, UNKNOWN.

## C9 — Health endpoints
Public `GET /healthz` returns only basic liveness. Protected owner/internal `GET /readyz` returns DB readiness, collector last-success timestamps, snapshot age, ETL age, DQ state.

## C10 — JWT verification
JWT validation must verify: cryptographic signature, `kid`, issuer, audience, expiration, not-before when present. Cache JWKS. On unknown key ID, refresh once and retry. Never implement decode-only JWT handling.

## C11 — Railway scheduling
Railway cron schedules use UTC. Store separately: `scheduled_for`, `started_at`, `retrieved_at`, `completed_at`. Never pretend the scheduled timestamp is the observation timestamp.

## C12 — Public export boundary
Create `make public-export` before `make publish-check`. Public exports must use an allowlisted schema. Never publish raw participant IDs, merchant IDs, rider hashes, order hashes, precise event timestamps capable of identifying an individual, raw H3 participant locations when unsafe, free text, or private source data. Then: `public-export` → `figures-public` → `publish-check`.

## C13 — Device timestamp quality
Store: `observed_at_device`, `received_at_server`, `device_clock_offset_ms`, `time_quality`. Possible `time_quality`: SERVER_SYNCED, RECENTLY_SYNCED, DEVICE_ONLY, UNKNOWN.

## C14 — Database constraints
Add appropriate DB CHECK constraints for obvious invariants: ETA low ≥ 0; ETA high ≥ ETA low; ETA upper reasonable; option count within protocol range; monetary amounts ≥ 0; item counts > 0; currency expected; appropriate lifecycle constraints where enforceable. Do not attempt impossible cross-row lifecycle constraints in SQL when ETL validation is the correct layer.

## C15 — Add first-class `studies`
Create `studies` containing at least: study_id, city, started_at, ended_at, protocol_version, experiment_protocol_hash, observation_protocol_hash, governance_version, status, final_snapshot_id. Observed records reference the study using a foreign key.

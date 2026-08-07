# 15 OWNER INPUTS REQUIRED

## Core Decisions Required Before ZonePilot

1. **Security & Data Integrity (P0)**
   - **Issue**: The current RLS policies allow total privilege escalation and cross-tenant data destruction.
   - **Input Required**: Should the audit fix these RLS policies to production-grade standards immediately, or will ZonePilot operate strictly in an isolated offline/laboratory environment where security is irrelevant?

2. **Database Performance (P1)**
   - **Issue**: The database lacks all foreign key indexes.
   - **Input Required**: Should we generate and apply a full indexing migration to prevent lockups during ZonePilot telemetry ingestion?

3. **Data Contamination (P0)**
   - **Issue**: The current ML and Dispatch pipelines use seeded deterministic values (sine waves, string hashes). 
   - **Input Required**: Do you explicitly authorize the complete QUARANTINE and architectural bypass of these synthetic modules so ZonePilot can build upon real data models?

4. **Telemetry Ingestion Engine**
   - **Issue**: Real GPS/location telemetry is missing.
   - **Input Required**: Will ZonePilot simulate live telemetry streams, or do we need to architect a new high-frequency data ingestion pipeline to capture real driver locations?

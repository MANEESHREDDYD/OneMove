# ZonePilot Threat Model (STRIDE Framework)

## 1. Threat Categories & Mitigations

### A. Spoofing
- **Threat**: Attacker crafts fake JWT token or spoofs participant ID in request body.
- **Mitigation**: Cryptographic JWT validation (`pyjwt`) verifying signature, allowed algorithm (`HS256`/`RS256`), expiration (`exp`), subject (`sub`), and expected issuer (`SUPABASE_JWT_ISSUER`). Server resolves participant identity strictly from verified token claims.

### B. Tampering
- **Threat**: Browser client submits unauthorized `study_id`, `participant_id`, or `study_phase` in POST payload.
- **Mitigation**: Pydantic schema model enforces `extra = "forbid"`, rejecting extra client-supplied metadata fields with `422 Unprocessable Entity`. Server resolves structural fields directly from trusted `assignments` table.

### C. Repudiation & Evidence Lineage
- **Threat**: Participant alters or deletes historical probe records after submission.
- **Mitigation**: Append-only storage model. Corrections insert a new observation referencing `supersedes_id`. RLS policies strictly forbid `DELETE` operations on `probe_observations`.

### D. Information Disclosure (IDOR)
- **Threat**: Participant A queries PostgREST or `/v1/probes` to read Participant B's telemetry or confidential study data.
- **Mitigation**: Database Row Level Security (RLS) policies enforce `participant_id == auth.uid()`. View `probe_observations_current` enforces `security_invoker = true` so caller RLS policies apply strictly to view queries.

### E. Denial of Service / Abuse
- **Threat**: Replay attack flooding endpoint with duplicate observations.
- **Mitigation**: Idempotent insert checks on `(participant_id, client_event_id)` uniqueness. Duplicate submissions return semantic success without duplicating physical database records.

### F. Privilege Escalation
- **Threat**: Volunteer or Observer attempts to claim `OWNER` role via metadata injection at signup.
- **Mitigation**: Role assignments stored in separate `participant_roles` table protected by RLS; `profiles` role defaults to customer/participant. Client metadata cannot grant administrative database privileges.

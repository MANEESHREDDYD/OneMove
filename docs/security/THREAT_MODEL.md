# Threat Model
- **T1**: Contamination of study data by unauthenticated actors. (Mitigation: Invite-only auth, strict RLS).
- **T2**: Cross-tenant data leakage. (Mitigation: RLS scoping by study_id and participant_id).
- **T3**: PII leakage in public export. (Mitigation: Strict schema allowlisting on export, HMAC identifiers).

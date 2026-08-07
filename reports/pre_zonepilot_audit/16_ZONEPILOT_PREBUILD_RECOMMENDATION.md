# 16 ZONEPILOT PREBUILD RECOMMENDATION

## FINAL DEPLOYMENT CLASSIFICATION
`NO-GO — FOUNDATION MUST BE REPAIRED`

## Rationale
The forensic audit proves that OneMove is an exceptional, high-fidelity UI demonstration, but it is structurally incapable of supporting a rigorous, data-driven ML experiment (ZonePilot) in its current state.

1. **P0 - Security & RLS**: The database lacks true multi-tenant isolation, allowing trivial privilege escalation and financial manipulation.
2. **P0 - Data Contamination**: The ML intelligence and dispatch engines are synthetic simulations, not trained algorithms. If ZonePilot is built atop them, the experimental validity is completely compromised.
3. **P1 - Missing Indexes**: The DB schema will suffer severe performance degradation during high-throughput data ingestion due to a total lack of foreign key indexes.

## Minimum Ordered Prerequisite Fixes (Before Day 1 of ZonePilot)
To unblock ZonePilot, the following exact sequence must be executed:

1. **Purge Synthetic P0 Generators**: Quarantine or delete the mock `onemove_intelligence/ml/` and `utils/pricing.ts` hashing logic to prevent experimental contamination.
2. **Rewrite DB Security (RLS)**: Apply production-grade RLS to `profiles`, `orders`, and `tracking` to lock down privilege escalation and cross-tenant PII leaks.
3. **Apply Database Indexes**: Run a database migration to apply `CREATE INDEX` on all core relational keys (e.g., `owner_id`, `customer_id`, `driver_id`).
4. **Establish Real Data Pipelines**: Replace the Faker generation scripts with an infrastructure capable of consuming or replaying real telemetry.

Once these 4 steps are complete, the foundation will achieve a `GO AFTER P0 FIXES` status, and ZonePilot implementation may safely commence.

# OneMove — CTO Production Readiness Matrix

**Baseline main:** `ec4bb92d38914910bfc6f0faabfdaea3919d6c65`
**Assessed:** 2026-08-19
**Assessor:** AUDIT-0 (single session — local worktree, read access to one hosted Supabase database, public GitHub metadata)

## Verdict

```
STATUS = NOT_CTO_PRODUCTION_READY
```

`P0_OPEN = 2`. `P1_OPEN` is not fully enumerated. Certification requires both at zero.

### Scope of this assessment — read this first

This matrix comes from **one session with local repository access, read access to one hosted
Supabase database, and public GitHub metadata**. It had **no** access to the GCP projects,
Cloud Run, Artifact Registry, Pub/Sub, Cloud Monitoring, the Supabase console, or any deployed
staging or production environment.

Every gate requiring deployed-environment evidence is recorded as `BLOCKED` — **not** as PASS
and **not** as FAIL. `NOT_PROVEN` means no evidence was gathered in either direction. Nothing
here should be read as "audited and found adequate" unless it says `PASS` with cited evidence.

---

## P0 — open

### P0-CREDENTIAL-001 — live database credential published to a public repository

| Field | Value |
|---|---|
| Status | **FAIL — rotation outstanding** |
| Repository | `github.com/MANEESHREDDYD/OneMove` — **PUBLIC** |
| Introduced | `daf7ca5` (2026-08-18), merged to `main` via PR #29 |
| Location | `services/common/db_dsn.py:15` (removed from working tree) |
| Secret fingerprint | `141b1191b1a7` (sha256 prefix — value never printed) |
| Affected project ref | `puygqvnhwsjkspoprfkb` (ap-southeast-1 pooler) |
| Exposure window | ~1 day on public `main`, and **permanent in git history** (`blob d61f6355`) |

**Aggravating finding.** The resolver did not merely *fall back* to this credential — it
**discarded any `DATABASE_URL` that did not match that one pooler host**, hard-pinning every
process to production. Neither `python-ci.yml` nor `zonepilot-release.yml` set `DATABASE_URL`,
so **every public CI run executed the full destructive pytest suite against the production
database.** This is the most likely origin of the accumulated test rows and of the 10
NULL-workspace snapshots recorded below.

**Remediated in code, verified:** no embedded credential; `DATABASE_URL` required outside tests;
`TEST_DATABASE_URL` required under pytest and refused when non-local or fingerprint-protected;
readiness fails without `DATABASE_URL`; secret scanner gates CI; both workflows now provision an
ephemeral local database.

**Outstanding — requires Supabase console access, cannot be done from this session:**

1. Rotate/revoke the `puygqvnhwsjkspoprfkb` database password.
2. Redistribute via Secret Manager to API, worker, dispatcher, ETL, and CI.
3. Prove old credential rejected and new credential accepted.
4. Review database audit logs for unauthorized access during the exposure window.
5. Decide history remediation — rewrite, or accept permanent exposure and rely on rotation.

### P0-AUTH-SNAPSHOT-001 — cross-tenant problem-snapshot access

**Status: application layer PASS (proven) · database layer NOT_PROVEN.**

Three compounding defects, all confirmed against live data:

1. `get_problem_snapshot` accepted `workspace_id` and never used it in SQL.
2. `service.py` persisted snapshots with **no workspace at all**.
3. The RLS policy contained `workspace_id IS NULL OR …`, granting unscoped snapshots to every tenant.

`OptimizationRepository._connect()` uses an **owner-role DSN, so RLS is not in force** on this
path. The missing predicate was the *only* control, not a defence-in-depth gap.

Exploitability demonstrated and closed against the real database — same row, old vs new predicate:

```
PRE-FIX  as tenant B -> {'snapshot_id': 'psnap-ae962488396edc5a', 'workspace_id': 'ws-isolation-a-7dca...'}
POST-FIX as tenant B -> None
```

Evidence: `tests/security/test_snapshot_tenant_isolation.py` — 6/6 pass against the real
database, including a positive control so the DENY assertions cannot pass vacuously.

**Blocking the database-layer fix:** migration `20260819000000_snapshot_tenant_isolation.sql`
deliberately refuses to apply while NULL-workspace rows exist. Live count at assessment:
**54 snapshots, 10 with NULL `workspace_id`.** The triage tool
`scripts/incident/triage_null_workspace_snapshots.py` is written and lint-clean, but **its SQL
has never been executed** — the snapshot database is reachable only with the compromised
credential. Precondition `ACTIVE_NULL_WORKSPACE_SNAPSHOTS = 0` is unmet.

### P0-ASSISTANT-TRUTH-001 — fabricated operational values

**Status: PASS in code · NOT_PROVEN in a deployed environment.**

Every fabricated value named in the mandate was present, plus fabricated evidence IDs
(`ev-dec-sample`) and a fabricated zone name. All removed; `create_default_registry` deleted
outright. Tools now read authoritative, provenance-carrying services. Ten tools with no
authoritative source are deliberately unregistered and return `UNAVAILABLE`. Provenance is
enforced structurally — `_provenance()` raises when artifact hash or source is absent, so an
unattributed number cannot reach a caller. Evidence: `tests/assistant/` 9/9 pass, one of which
exercises the real gold artifacts.

Not yet satisfied: the full per-value evidence envelope the mandate specifies (`dataset_id`,
`evidence_class`, `information_available_at`, `request_id`, `trace_id`), and Assistant-vs-source
equality testing across multiple zones.

---

## Certification gates

Legend — `PASS` verified with cited evidence · `FAIL` verified defective · `NOT_PROVEN` no
evidence gathered · `BLOCKED` requires access unavailable to this assessment.

| Domain | Status | Evidence / why not |
|---|---|---|
| Credential security | **FAIL** | Public exposure confirmed; code fixed, rotation outstanding |
| Tenant isolation (application) | **PASS** | Exploit reproduced then closed; 6/6 real-DB tests |
| Tenant isolation (database/RLS) | **NOT_PROVEN** | Migration blocked by 10 NULL rows; unapplied |
| Assistant truth | **PASS (code)** | Fixtures removed; 9/9 tests; deployed behaviour unverified |
| Assistant evidence envelope | **FAIL** | Full field set not implemented |
| Full tenant attack suite | **NOT_PROVEN** | Only snapshot/replay/decision vectors covered; JWT forgery, role escalation, header forgery untested |
| Database schema | **FAIL** | `workspace_id` is nullable `TEXT` on jobs and snapshots, not `UUID NOT NULL` FK |
| Runtime DDL | **PASS** | Both runtime `CREATE TABLE` blocks removed; migrations own schema |
| Snapshot content/ownership split | **NOT_PROVEN** | Two-table design not implemented; no ADR |
| Outbox claim protocol | **FAIL** | No `lease_owner`, `fencing_token`, or `CLAIMED` state; `attempts` only |
| Repository scoping CI rule | **FAIL** | Static check not implemented |
| CI secret scanning | **PASS** | `scripts/security/scan_secrets.py`; tree PASS, history FAIL (expected) |
| CI database isolation | **PASS (config)** | Both workflows now set `TEST_DATABASE_URL`; not yet observed green in CI |
| Auth / JWT hardening | **NOT_PROVEN** | Not reviewed this session |
| IAM / WIF | **BLOCKED** | No GCP access |
| Cloud Run / networking | **BLOCKED** | No GCP access |
| Supply chain / SBOM / provenance | **NOT_PROVEN** | Not reviewed |
| Same-digest promotion | **BLOCKED** | No Artifact Registry access |
| Rate limiting | **FAIL** | Per-instance in-memory limiter is not authoritative under horizontal scale |
| Caching / CDN | **NOT_PROVEN** | No explicit policy found |
| Observability / logging | **NOT_PROVEN** | Not reviewed |
| Alert fire test | **BLOCKED** | Requires staging plus monitoring access |
| Full deployed E2E | **BLOCKED** | Requires deployed environment |
| Load / breakpoint | **BLOCKED** | Requires deployed environment |
| Chaos | **BLOCKED** | Requires deployed environment |
| Backup / restore / DR / RPO / RTO | **BLOCKED** | Requires database platform access |
| Rollback | **NOT_PROVEN** | Not exercised |
| ETL / data quality / schema evolution | **NOT_PROVEN** | Not reviewed |
| Forecast truth / model governance | **NOT_PROVEN** | Not reviewed |
| Optimizer / assumptions registry | **FAIL** | Business proxies still live in router constants |
| Decision ledger / PIT replay | **PASS (partial)** | Replay now fails closed without an explicit workspace; 48/48 pass |
| Frontend / accessibility / UX | **NOT_PROVEN** | Not reviewed |
| Documentation / runbooks | **FAIL** | Sprawl and legacy marketplace/study docs remain |
| Cost / FinOps | **BLOCKED** | No billing access |

---

## Test posture change — intended, not a regression

Removing the credential fallback means DB-backed tests can no longer silently reach a hosted
database. Without `TEST_DATABASE_URL`: **199 passed, 56 skipped, 5 failed, 18 collection errors.**
All 23 failures and errors are the same intended `DatabaseConfigurationError`. CI now provisions
an ephemeral local Supabase and applies migrations, which is where these must run.

18 modules construct repositories at *import* time, so absent configuration surfaces as a
collection error rather than a skip. Worth restructuring; not a correctness defect.

## Known limitations of this matrix

- No independent multi-agent audit board was run. This is a single assessor, so no separation
  between implementer and certifier was achieved.
- No deployed environment was observed. Every cloud, load, chaos, DR, and alerting claim is unverified.
- The triage SQL has never been executed.
- `P1_OPEN` is not fully enumerated — domains marked `NOT_PROVEN` were not searched for defects.

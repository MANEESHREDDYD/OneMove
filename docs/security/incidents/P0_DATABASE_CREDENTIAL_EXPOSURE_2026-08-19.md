# P0-CREDENTIAL-001 — Database credential exposed in a public repository

| Field | Value |
|---|---|
| Incident ID | P0-CREDENTIAL-001 |
| Severity | P0 |
| Status | **OPEN** — containment partial, eradication blocked on credential rotation |
| Opened | 2026-08-19 |
| Product | OneMove |
| Repository | `github.com/MANEESHREDDYD/OneMove` (**public**) |
| Affected project ref | `puygqvnhwsjkspoprfkb` (Supabase, ap-southeast-1 pooler) |
| Secret fingerprint | `141b1191b1a7` (sha256 prefix of the value; the value itself is never recorded here) |

No secret value appears in this document. Credentials are referred to only by
fingerprint so that this record can be circulated without extending the exposure.

---

## Summary

A live PostgreSQL/Supabase database password was committed to a public GitHub
repository as a hard-coded fallback inside the application's DSN resolver. The
same resolver actively discarded correctly-configured environment overrides,
which meant every process that did not match one specific pooler host — including
the automated test suite in public CI — connected to the production database.

The credential must be treated as permanently compromised. It is present in git
history and cannot be removed by a code change.

---

## Timeline (UTC+05:30 where stated)

| When | Event |
|---|---|
| 2026-08-18 21:32 | Commit `daf7ca5` ("R0-R9 release candidate", PR #29) introduces the credential in `services/common/db_dsn.py`. Merged to `main`. |
| 2026-08-18 → 2026-08-19 | Credential live on public `main`. Every push/PR CI run executes the destructive pytest suite against the production database. |
| 2026-08-19 | Discovered during an unrelated tenant-isolation audit of the same file's callers. |
| 2026-08-19 | Repository confirmed **public** via GitHub API. Exposure reclassified from "bad practice" to active incident. |
| 2026-08-19 | Containment: resolver rewritten, CI database isolated, secret scanning gate added. Committed to `hotfix/onemove-p0-security-incident`. |
| — | **Pending:** credential rotation at the provider. Incident remains open. |

Exposure window on public `main`: approximately one day. This is **not**
mitigating. Public repositories are scraped continuously by automated
credential harvesters, typically within minutes of a push.

---

## Root cause

`services/common/db_dsn.py` resolved the database DSN as follows:

1. Read `DATABASE_URL` / `EXECUTION_DATABASE_URL` from the environment.
2. **Reject it unless it contained one specific pooler hostname.**
3. Otherwise return a hard-coded literal containing production credentials.

Step 2 is the aggravating factor and distinguishes this from an ordinary
hard-coded fallback. A correctly-provisioned environment variable pointing at a
local or staging database was silently discarded in favour of production. There
was no configuration a developer or CI job could supply that would avoid
production, short of editing the source.

Contributing factors:

- Neither `python-ci.yml` nor `zonepilot-release.yml` set `DATABASE_URL`, so CI
  inherited the hard-coded production target.
- No secret scanning existed in CI, so the credential passed review and merged.
- 18 test modules construct repositories at import time, so the production
  connection was established during test *collection*, before any test opted in.

---

## Impact

**Confirmed:**

- A live production database credential was publicly readable for ~1 day and
  remains in public git history (blob `d61f6355`).
- Public CI executed the full destructive test suite against the production
  database on every push and pull request, including from Dependabot branches.
- The production database contains test-created rows. At assessment time the
  snapshot table held 54 rows, of which 10 had a NULL `workspace_id` — the most
  likely origin being CI-executed tests that predate workspace enforcement.

**Not established (see Remaining uncertainty):**

- Whether any third party used the credential.
- The full inventory of CI-created rows across all tables.

**Blast radius of the credential itself:** the DSN uses the pooler role, which in
this deployment is an owner-level role. Row Level Security does **not** constrain
it. Anyone holding the credential had unrestricted read and write access to all
tenant data, bypassing the entire application authorization layer.

---

## Affected systems

| System | Exposure |
|---|---|
| Supabase project `puygqvnhwsjkspoprfkb` | Direct — credential grants owner-role access |
| GitHub Actions (`python-ci`, `zonepilot-release`) | Executed destructive tests against production |
| API / worker / dispatcher / ETL | Resolved the same hard-coded credential when `DATABASE_URL` did not match the pinned host |
| Local developer environments | Same — any `pytest` invocation reached production |

---

## Containment (done)

Committed on `hotfix/onemove-p0-security-incident`:

- `db_dsn.py` rewritten. No source-code credential. `DATABASE_URL` is required
  outside tests; absence raises `DatabaseConfigurationError` rather than
  connecting somewhere.
- Under pytest the DSN comes from `TEST_DATABASE_URL`, and a non-local or
  fingerprint-protected target is refused outright.
- Readiness probe fails when `DATABASE_URL` is unset in staging/production, so a
  misconfigured revision cannot take traffic.
- Both CI workflows provision an ephemeral local PostgreSQL and export
  `TEST_DATABASE_URL`. CI never receives a production credential.
- `scripts/security/scan_secrets.py` added and wired as a blocking CI gate.
- Regression tests assert the module source contains no embedded credential and
  that fail-closed behaviour holds.

Verified: DB-backed tests now abort with an actionable configuration error
instead of silently reaching production.

## Eradication (outstanding — requires provider console access)

1. **Rotate/revoke** the database password for project `puygqvnhwsjkspoprfkb`.
2. Store the new value in GCP Secret Manager; distribute to API, worker,
   dispatcher, and ETL/acquisition. CI must **not** receive it.
3. Prove `OLD_CREDENTIAL_AUTH = REJECTED` and `NEW_CREDENTIAL_AUTH = ACCEPTED`,
   recording only the outcome and fingerprints.
4. Decide on history remediation: rewrite history (coordinated force-push,
   invalidates existing clones and forks) versus accept permanent exposure and
   rely on rotation. Rotation is the control that actually matters; history
   rewriting does not help if a copy was already taken.

## Recovery (outstanding)

- Execute `scripts/incident/triage_null_workspace_snapshots.py` against the
  rotated database. Precondition for the tenant-isolation migration is
  `ACTIVE_NULL_WORKSPACE_SNAPSHOTS = 0`.
- Produce `TEST_DATA_INCIDENT_INVENTORY.json` for CI-created pollution. Clean up
  only high-confidence test artifacts; quarantine anything ambiguous.
- Apply the snapshot tenant-isolation migration against a clean integration
  database and verify schema, RLS, and indexes.

## Preventive controls

| Control | Status |
|---|---|
| No source-code credential literals | Implemented + regression test |
| Fail-closed configuration resolution | Implemented + regression test |
| Test suite refuses non-local databases | Implemented + regression test |
| Secret scanning gate in CI (working tree) | Implemented, blocking |
| Secret scanning over git history | Implemented, advisory |
| CI provisions its own ephemeral database | Implemented |
| Readiness fails on missing DB config | Implemented |
| Branch protection requiring the secret gate | **Not implemented** |
| Provider-side IP allow-listing / network restriction | **Not implemented** |
| Least-privilege application role (not owner) | **Not implemented** — RLS is bypassed today |
| Periodic credential rotation | **Not implemented** |

---

## Remaining uncertainty

Recorded honestly; these are open, not closed.

1. **No log review has been performed.** Database audit and connection logs for
   the exposure window have not been examined. Whether any unauthorized access
   occurred is `UNKNOWN`. Required classification per connection — `CONFIRMED_CI`,
   `CONFIRMED_APPLICATION`, `UNKNOWN`, `SUSPICIOUS` — has not been produced,
   because it needs Supabase console access that was unavailable.
2. **Test-data pollution is unquantified** beyond the snapshot table.
3. **The triage tooling is unexecuted.** Its SQL has never run against a live
   database; it is written and lint-clean but unvalidated.
4. **Fork/clone exposure is unbounded.** Any fork, clone, or cache taken while the
   credential was live retains it regardless of what happens to `main`.

## Lessons

- A hard-coded fallback that *overrides* explicit configuration is far more
  dangerous than one that merely fills a gap. It removes the operator's ability
  to opt out.
- Import-time construction of database clients means "collection" already
  connects. Tests could not opt out of production before running.
- The absence of a secret-scanning gate allowed this through code review; the gate
  is cheap and should have predated the first database integration.

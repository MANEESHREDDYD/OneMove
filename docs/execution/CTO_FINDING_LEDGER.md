# OneMove — CTO Finding Ledger

**Baseline main:** `ec4bb92` · **Branch head:** `75da167` (`hotfix/onemove-p0-security-incident`)
**Regenerated:** 2026-08-20

Findings are immutable. Severity is never lowered to reach a release. A finding leaves
`OPEN` only via a fix commit plus a regression test, and reaches `PASS` only when an
auditor who did not write the fix retests it.

> **This document was regenerated, not patched.** Earlier revisions were edited
> incrementally and drifted: a stale head SHA, prose that contradicted its own summary
> table, and a P0 count that excluded F-019 while F-019 was still recorded P0 and unfixed.
> The arithmetic below is derived from the finding rows and reconciled.

## Severity is fixed at discovery

| Severity | Total | Ready for retest | In remediation | Blocked external | Open |
|---|---|---|---|---|---|
| **P0** | 16 | 13 | 1 | 1 | 1 |
| **P1** | 11 | 7 | 0 | 0 | 4 |
| **P2** | 1 | 0 | 0 | 0 | 1 |
| **Total** | **28** | **20** | **1** | **1** | **6** |

`16 + 11 + 1 = 28` · `20 + 1 + 1 + 6 = 28`

```
PASS = 10    REOPENED_BY_CERTIFICATION = 3    AWAITING_RE-CERTIFICATION = 2
BLOCKED_EXTERNAL = 1    OPEN (never started) = 6    IN_REMEDIATION = 1
P0_NOT_CERTIFIED = 8     P1_NOT_CERTIFIED = 5     P2_NOT_CERTIFIED = 1
STATUS = NOT_CTO_PRODUCTION_READY
```

**`PASS = 0` is the number that governs.** "Ready for retest" is not "passed". Every fix
recorded here was written by the agent that verified it, and no independent auditor has
certified any of them. F-019 remains **P0 and open**; it is not reclassified to make a
count look better.

## What "verified" means per row

23 findings were reproduced against the code before being fixed — 19 by me directly, 4
(F-012 to F-015) by the frontend fixer, of which I independently spot-checked F-015's
unauthenticated service-role route handler. 5 remain unreproduced agent reports. Treat
those as leads, not facts: several agent claims in this programme proved imprecise, and
two proved understated.

---

## P0 — ready for independent retest (13)

| ID | Title | Fix | Regression test |
|---|---|---|---|
| F-003 | Fabricated Assistant operational values | `a6d2e51` | `test_typed_assistant.py` |
| F-004 | Assistant evidence IDs did not resolve through the Inspector | `425952d` | `test_typed_assistant.py` |
| F-005 | Decision ledger forgeable via request defaults | `5c5516f` | `test_snapshot_tenant_isolation.py` |
| F-006 | Optional workspace predicate in five repositories | `e8e9ef5` | `test_repository_tenancy_contract.py` |
| F-007 | `GRANT ALL` to anon/authenticated; 6 tables had no RLS | `5bbb384` | `test_database_grants_contract.py` |
| F-008 | Outbox claim was a no-op; no lease or fencing | `2be6f15` | `test_outbox_fencing_contract.py` |
| F-010 | Synthetic travel matrix labelled `PUBLIC_GEOGRAPHIC` | `941d56a` | `test_provenance_truth.py` |
| F-011 | `save_result` invented code_sha/graph/solver lineage | `941d56a` | `test_provenance_truth.py` |
| F-012 | Executive page fabricated HEALTHY/DEGRADED | `fe04099` | tsc + next build |
| F-013 | Compliance console fabricated incidents and people | `fe04099` | FEATURE_NOT_CONNECTED |
| F-014 | `Math.random()` ML confidence persisted and displayed | `fe04099` | null + UNAVAILABLE |
| F-015 | Admin authz: 8 pages + 4 server entry points unguarded | `fe04099` | `lib/auth/dal.ts` + `proxy.ts` |
| F-018 | Forecast fabricated provenance; `0.0`; coverage `1.0` | `7c5996c` | `test_forecast_truth.py` |

## P0 — not closed (3)

| ID | Status | Title | Why it is not closed |
|---|---|---|---|
| F-001 | `BLOCKED_EXTERNAL` | Live DB credential in public repo | Code remediated (`df4ef8f`) and tested. The credential itself requires provider rotation and is permanent in public history (blob `d61f6355`). |
| F-002 | `IN_REMEDIATION` | Cross-tenant problem-snapshot read | Application layer closed (`d1028c2`), exploit reproduced then proven closed against the real DB. The enforcement migration is blocked behind 10 NULL-workspace rows awaiting triage. |
| F-019 | `OPEN` | Optimizer business constants are literals in router code | **P0, unreproduced, unfixed.** Not started. |

## P1 — ready for independent retest (7)

| ID | Title | Fix | Regression test |
|---|---|---|---|
| F-009 | Lost-lease writer could mark PUBLISHED | `2be6f15` | `test_outbox_fencing_contract.py` |
| F-016 | JWT: `exp` not required; issuer unverified when unconfigured | `9c3d378`, `9ed8b8e` | `test_jwt_hardening.py` |
| F-017 | Workflows lacked least-privilege token permissions | `71d50ea` | `test_workflow_permissions.py` |
| F-020 | PIT split defaulted to `event_time` | `4d33a4f` | `test_pit_leakage.py` |
| F-022 | Worker lease < ack deadline; unfenced result write | `54c5ace` | `test_outbox_fencing_contract.py` |
| F-024 | Import-time DB coupling broke liveness and collection | `e7f3186` | imports + `/healthz` 200 with no DB |
| F-026 | `datetime.timezone` misuse produced an uncaught 500 | `71d50ea` | `test_events_timezone_regression.py` |

## P1 — open (4)

| ID | Domain | Title | Verified? |
|---|---|---|---|
| F-021 | reliability | DLQ topic has no subscription; alert matches all topics; no notification channel | reported only |
| F-023 | rate limiting | Per-process in-memory limiter across 10 instances; unbounded window dict | reported only |
| F-025 | api | Incompatible error taxonomies | **partially verified** — see below |
| F-028 | a11y | No skip link, no `aria-live`/`aria-current`, no reduced-motion; axe gate permits 5 critical | reported only |

**F-025 gained evidence this run.** Classifying every suite failure showed database
unavailability surfacing as `422 VALIDATION_FAILED` and as unhandled `500`s on several
routes, where it must be `503 DEPENDENCY_UNAVAILABLE`. A wrong status code here is not
cosmetic: it tells a client that a retryable dependency outage is a permanent client error.

## P2 — open (1)

| ID | Title |
|---|---|
| F-027 | Documentation sprawl: 135 docs, 25 ZonePilot-branded including canonical `ARCHITECTURE.md`; legacy ride/checkout reports remain |

---

## Two remediations that created defects

Recorded because they are the argument for independent certification, not footnotes.

**F-004 was created by the fix for F-003.** I emitted composite strings as evidence IDs
and wrote a docstring asserting they resolve through the Evidence Inspector. They resolved
nowhere. A separate auditor caught it.

**F-016's fix regressed JWT diagnostics.** Requiring `exp`/`sub` inside `jwt.decode` moved
the missing-sub rejection into PyJWT, collapsing a specific message into a generic one and
breaking a pre-existing test. Found only by classifying each failure individually instead
of repeating the claim that all failures were configuration-related. Repaired in `9ed8b8e`.

## Test posture

```
392 passed · 23 failed · 56 skipped · 0 collection errors
```

All 23 failures are classified with evidence, not assumed: 10 raise
`DatabaseConfigurationError` directly, 12 assert on a database-unavailability response,
1 is a `KeyError` cascading from a 503. None indicates a defect in application logic.

## Certification gaps that no amount of local work closes

- **No live PostgreSQL.** F-007's grants, F-008's two-dispatcher race, and F-022's
  concurrent-worker case are asserted as static contracts. The Docker daemon is
  unresponsive, so none has been executed against a real database.
- **No deployed environment.** Staging E2E, load, soak, chaos, DR, rollback, alert-fire,
  IAM, and same-digest promotion are all `NOT_RUN`.
- **No independent certifier has run since the fixes landed.**

---

## Certification wave 1 — 2026-08-20, at `b3406f6`

Three read-only certifiers retested the fixed state. Not one of them wrote the code
it reviewed. Result: **6 PASS, 5 FAIL** on first pass.

### PASS (10 findings)

F-003, F-004 (Assistant evidence round-trip traced end-to-end through the real
Inspector), F-007 (all 11 tables enable RLS; REVOKE ordering correct), F-008, F-009
(claim atomicity and fencing hold; no overlap interleaving could be constructed),
F-015 (all 7 admin server entry points guarded — the certifier found a 5th file the
fix list had missed and confirmed it too), F-016, F-017, F-022, F-024.

### FAIL — and what they caught

| ID | Verdict | Defect found in the *fix* |
|---|---|---|
| F-001 | FAIL | Rotation outstanding; `ALLOW_NONLOCAL_TEST_DATABASE=1` was a self-service opt-out; `PROTECTED_DATABASE_FINGERPRINTS` empty by default and therefore inert |
| F-006 | FAIL | **The contract test was evadable**: `get_job` absent from the checked set, `async def` skipped the walk entirely, regex matched one literal spelling |
| F-011 | FAIL | **Hard regression**: the fail-closed call site omitted three now-required arguments → `TypeError` on the first solver failure. Also placeholder lineage, and `code_sha` never persisted |
| F-010 | FAIL | Scenario row persisted *before* the matrix check (orphan rows); `ResilienceEngine` hardcodes coverage/capacity/zone counts, so grades are invented — same defect class as the deleted matrix generator |
| F-018 | FAIL | `mae`/`rmse` set to `0.0` when zero samples were scored, with `sample_count` counting skipped samples — a perfect-accuracy claim over no measurement |
| F-020 | FAIL | `evaluator.py` still splits on `observation_time`; `get_zone_forecasts` has no `forecast_issue_time <= decision_time` filter, so a future-issued forecast is selectable |

### Repaired in `75da167`, awaiting re-certification

**F-011** and **F-006**. The F-006 repair was verified against each of the three
bypasses the certifier named. F-001's blanket override is gone, but F-001 stays
`BLOCKED_EXTERNAL` on rotation.

### Reopened, not yet fixed

**F-010**, **F-018**, **F-020**. Severity unchanged; they revert to open rather than
becoming new findings, because a defect surviving its own remediation is the same
defect.

### Residuals the certifiers flagged (not yet findings)

- Outbox: a poison payload aborts a whole claimed batch, stranding siblings with
  burned attempts; when Pub/Sub is unconfigured locally, claimed rows exhaust all
  attempts and dead-letter without a publish ever being attempted.
- Worker: `save_result`'s boolean is discarded, so a lost-lease worker still logs
  "solved successfully" — hiding a duplicate solve from monitoring.
- `/readyz` returns 500 rather than 503 when `DATABASE_URL` is unset and
  `ENVIRONMENT` is not staging/production.

### Standing conclusion

Five of eleven certified fixes were defective, and two of those defects were
*created* by the remediation itself. No fix in this programme should be trusted
because its author tested it.

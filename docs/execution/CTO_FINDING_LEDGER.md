# OneMove — CTO Finding Ledger

**Baseline main:** `ec4bb92` · **Branch head:** `ca177b7` (`hotfix/onemove-p0-security-incident`)
**Regenerated:** 2026-08-20, after certification wave 1

Findings are immutable. Severity is fixed at discovery and never lowered to reach a
release. A finding reaches `PASS` only when a certifier who did not write the fix
retests it and fails to break it.

> Regenerated whole, not appended. A previous revision was appended to and immediately
> contradicted itself — the header still read `PASS = 0` while the new section recorded
> `PASS = 10`. The counts below are derived from the finding rows.

## State after certification wave 1

| Severity | Total | PASS | Awaiting re-cert | Reopened | Ready, uncertified | In remediation | Blocked ext. | Open |
|---|---|---|---|---|---|---|---|---|
| **P0** | 16 | 5 | 8 | 0 | 0 | 1 | 1 | 1 |
| **P1** | 11 | 4 | 5 | 0 | 0 | 0 | 0 | 2 |
| **P2** | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **Total** | **28** | **9** | **13** | **0** | **0** | **1** | **1** | **4** |

`16 + 11 + 1 = 28` · `9 + 13 + 0 + 0 + 1 + 1 + 4 = 28`

```
PASS = 9         P0_NOT_CERTIFIED = 11   P1_NOT_CERTIFIED = 7    P2_NOT_CERTIFIED = 1
STATUS = NOT_CTO_PRODUCTION_READY
```

## Wave 3 — repairs since wave 2, all awaiting certification

| ID | Sev | Fix | What changed |
|---|---|---|---|
| F-005 | P0 | `7490ae3` | Hand-authored decisions must declare `MANUAL_OPERATOR_DECISION` + rationale; marker persisted. Values still unvalidated — **stays open** |
| F-007 | P0 | `818f8dc` | **PASS revoked.** Blanket revoke broke `profiles`/`workspaces`/`weather`; now scoped to the ten OneMove tables |
| F-010 | P0 | `ca177b7` | Metrics derived from the frozen matrix or unavailable; invented constants gone; ordering fixed |
| F-011 | P0 | `46b7395` | `code_sha` persisted; placeholder lineage removed; fails closed |
| F-018 | P0 | `2b9148c` | Zero scored samples ⇒ mae/rmse/coverage null, not 0.0; observed 0.0 still distinguishable |
| F-020 | P1 | `2b9148c` | Evaluation and reads bounded by `information_available_at` / `forecast_issue_time` |
| F-025 | P1 | `db31871` | One canonical envelope; DB outage ⇒ 503 centrally, not 422/500 |
| F-006 | P0 | `75da167` | Contract test hardened against all three bypasses |

### F-007 demoted from PASS — the most important entry here

F-007 was certified PASS on **static** review. Executing the migration against a live
PostgreSQL in CI produced **30 `InsufficientPrivilege` failures**, 16 across the
RLS/tenancy suite, on `weather`, `workspaces`, `workspace_members` and `profiles`.
`REVOKE ALL ON ALL TABLES` followed by re-granting only ten tables stripped everything
else — including `profiles`, which the admin-role check reads.

**A static certification that a live database contradicts was not a certification.**

### F-016 and F-015 → NEEDS_RECERTIFICATION

Not defects. The canonical error contract changed auth error RESPONSE bodies
(`trace_id` added; `HTTP_500`/`HTTP_503` → `INTERNAL_ERROR`/`DEPENDENCY_UNAVAILABLE`).
No authorization decision changed and `auth.py` is untouched, but their certification
evidence pinned response bodies, so the prior PASS cannot be assumed to survive.

### Live-database evidence, first time in this programme

CI ran the suite against ephemeral PostgreSQL: **443 passed, 23 failed, 17 skipped**
(local, no DB: 501/22/56). Splitting the secret scan into its own job is what made this
possible — as a step it aborted the job before any test ran.

## Certification wave 2 — AUDIT-0 and AUDIT-4, at `46b7395`

Both had never certified against the fixed state. **Result: 4 PASS, 1 FAIL.**

| ID | Sev | Verdict | Evidence |
|---|---|---|---|
| F-012 | P0 | **PASS** | Every tile carries a required `source` prop and a snapshot timestamp; P95 renders UNAVAILABLE because no such metric is computed; the defensibility claim is gone |
| F-013 | P0 | **PASS** | Page is 63 lines, one FEATURE_NOT_CONNECTED card, no incident IDs, no person names, no enforcement control |
| F-014 | P0 | **PASS** | `confidence_score: null` persisted; UI renders Unavailable; whole-frontend sweep found `Math.random` only in docstrings |
| F-026 | P1 | **PASS** | Exercised the real route: naive `observed_at_device` → 200 with correct UTC normalisation, no 500 |
| F-005 | P0 | **FAIL** | Required is not validated — see below |

### F-005 — reopened, partially addressed in `7490ae3`

AUDIT-0 posted invented facilities, an invented OSRM hash and 100% coverage to
`POST /decisions` and received **201 with a persisted decision_id**. Requiring the
fields stopped an empty body, not a well-formed fiction.

**My test change had pinned the forgery.** Updating the durable-decisions test to supply
`graph_version`/`solver_version` made a hand-authored decision return 201 and asserted
that as correct. I treated a failing test as a payload to repair rather than asking
whether the endpoint should accept it.

`POST /decisions/freeze` was certified sound: it reconstructs every field from stored
optimization state, reads the OSRM hash from the gold manifest rather than the payload,
and returns 422 for a failed job, a resultless job, or one outside the caller's workspace.

Partially addressed: the free-form path now requires
`decision_class="MANUAL_OPERATOR_DECISION"` plus a rationale, and persists that marker
onto the record so a reader can distinguish hand-authored from solver-derived.
**F-005 stays open** — the numbers are honestly labelled but still unvalidated against
the facility catalog and release manifest.

### Certified caveats worth carrying forward

- `tests/api/test_events_timezone_regression.py` is mostly source-text assertion; it
  would pass if the handler were deleted. F-026 passed on the certifier's live request,
  not on that test.
- `events.py` persists and hashes `observed_at_device` **un-normalised** while computing
  the deviation from a UTC-coerced copy — a consistency gap, not a 500.
- Local `.next/` build output still contains pre-fix strings (`INC-88921`, `Richard Roe`,
  `Times Square`). It is **not** committed (`git ls-files` → 0 matches, `.gitignore:5`),
  but must be deleted before any artifact upload. Source maps embed the historical
  strings via the new docstrings.

### F-028 measured state (open, unfixed)

Axe gate is `toBeLessThanOrEqual(5)` critical violations on ONE route
(`tests/e2e/onemove-accessibility.spec.ts:26`), filtering out serious/moderate entirely.
No skip link. Two unlabelled `<nav>` elements. Zero `aria-current`, zero `aria-live`.
Six `htmlFor` against 24 inputs — roughly 75% unlabelled, with no `aria-invalid`/
`aria-describedby`. Heading level skipped in the compliance card. No
`prefers-reduced-motion` anywhere, while animation utilities are in active use.

---

## Certification wave 1 — three independent read-only certifiers, at `b3406f6`

None of them wrote the code it reviewed. **First-pass result: 6 PASS, 5 FAIL.**

### PASS (10)

| ID | Sev | What the certifier verified |
|---|---|---|
| F-003 | P0 | No fabricated operational values remain |
| F-004 | P0 | Evidence round-trip traced end to end through the real Inspector; the test resolves rather than asserting string shape |
| F-007 | P0 | All 11 tables enable RLS; `authenticated` gets SELECT only; REVOKE ordering correct |
| F-008 | P0 | Claim atomicity holds; no overlapping interleaving could be constructed |
| F-015 | P0 | All 7 admin server entry points guarded — the certifier found a 5th file the fix list had missed and confirmed it too |
| F-009 | P1 | Fencing predicate on both finalizers; stale holder updates 0 rows |
| F-016 | P1 | `exp`/`sub` required; alg confusion blocked; issuer fail-closes |
| F-017 | P1 | All 8 workflows declare least privilege |
| F-022 | P1 | Lost-lease worker cannot write a result |
| F-024 | P1 | API imports and `/healthz` 200 with no DB; `/readyz` 503 when DB unreachable |

### FAIL — what certification caught in the fixes

| ID | Sev | Defect found in the remediation |
|---|---|---|
| F-001 | P0 | Rotation outstanding; `ALLOW_NONLOCAL_TEST_DATABASE=1` was a self-service opt-out; `PROTECTED_DATABASE_FINGERPRINTS` empty by default and inert |
| F-006 | P0 | **The contract test was evadable**: `get_job` absent from the checked set, `async def` skipped the AST walk entirely, regex matched one literal spelling |
| F-011 | P0 | **Hard regression**: the fail-closed call site omitted three now-required arguments → `TypeError` on the first solver failure. Also placeholder lineage; `code_sha` never persisted |
| F-010 | P0 | Scenario row persisted *before* the matrix check; `ResilienceEngine` hardcodes coverage/capacity/zone counts, so grades remain invented — the same defect class as the deleted matrix generator |
| F-018 | P0 | `mae`/`rmse` set to `0.0` when zero samples scored, `sample_count` counting skipped samples — perfect accuracy claimed over no measurement |
| F-020 | P1 | `evaluator.py` still splits on `observation_time`; `get_zone_forecasts` has no `forecast_issue_time <= decision_time` filter, so a future-issued forecast is selectable |

### Repaired — awaiting re-certification (1)

**F-006** (`75da167`). Verified against each of the three bypasses the certifier named.
Not `PASS`: the same agent wrote and verified the repair.

### F-011 — returned to remediation, then repaired again (`46b7395`)

The `75da167` repair fixed only the `TypeError`. It did **not** close the provenance
defect, so F-011 was correctly returned to `IN_REMEDIATION` rather than left awaiting
re-certification. Two defects survived that repair:

  * `"UNKNOWN"` / `"UNVERSIONED"` were substituted whenever the job row lacked a value,
    in the service fail-closed path and both worker paths. Invented provenance wearing
    the shape of real provenance — worse than a null, because it looks attributable.
  * `code_sha` was required by `save_result` and then discarded: the column did not
    exist on `optimization_results` and was absent from the INSERT.

Both closed in `46b7395`. Migration `20260820001000` adds `code_sha`,
`dataset_version`, `matrix_id`, `matrix_sha256`, `problem_snapshot_id/sha256` and
`solver_config_hash` to `optimization_results`, denormalised deliberately: the result
is immutable evidence, the job row is not. All four call sites now fail closed on
missing frozen lineage. Awaiting re-certification.

`ALLOW_NONLOCAL_TEST_DATABASE` is gone, replaced by per-database fingerprint
authorisation, but **F-001 stays blocked on rotation**.

### Reopened, unfixed (3)

**F-010**, **F-018**, **F-020** — at unchanged severity. A defect surviving its own
remediation is the same defect, not a new one.

---

## Not yet certified

**Ready, uncertified (5):** F-005, F-012, F-013, F-014 (P0), F-026 (P1) — fixed with
regression tests, no certifier has retested them.

**In remediation (1):** F-002 — application layer closed and the exploit proven closed
against the real DB; the enforcement migration is blocked behind 10 NULL-workspace rows
awaiting triage.

**Blocked external (1):** F-001 — rotation requires provider access; the credential is
permanent in public history (blob `d61f6355`).

**Open, never started (6):** F-019 (P0, optimizer constants in router code), F-021,
F-023, F-025, F-028 (P1), F-027 (P2).

**F-025 gained evidence:** classifying every suite failure showed database unavailability
surfacing as `422 VALIDATION_FAILED` and unhandled `500`s where it must be `503`. That
tells a client a retryable outage is a permanent client error.

## Residuals certifiers flagged (not yet findings)

- Outbox: a poison payload aborts a whole claimed batch, stranding siblings with burned
  attempts; with Pub/Sub unconfigured locally, claimed rows exhaust all attempts and
  dead-letter without a publish ever being attempted.
- Worker: `save_result`'s boolean is discarded, so a lost-lease worker still logs
  "solved successfully", hiding a duplicate solve from monitoring.
- `/readyz` returns 500 rather than 503 when `DATABASE_URL` is unset and `ENVIRONMENT`
  is not staging/production.

## Test posture

```
395 passed · 23 failed · 56 skipped · 0 collection errors
```

All 23 failures classified with evidence, not assumed: 10 raise
`DatabaseConfigurationError` directly, 12 assert on a database-unavailability response,
1 is a `KeyError` cascading from a 503. None indicates a defect in application logic.

## Standing conclusion

Five of eleven certified remediations were defective, and two of those defects were
*created* by the remediation itself (F-004 by the fix for F-003; the JWT diagnostic
regression by the fix for F-016). **No fix in this programme should be trusted because
its author tested it.**

## Gaps no amount of local work closes

- **No live PostgreSQL** — the Docker daemon is unresponsive. F-007's grants, F-008's
  two-dispatcher race and F-022's concurrent-worker case are certified as static
  contracts only; empirical concurrency is `NOT_PROVEN`.
- **No deployed environment** — staging E2E, load, soak, chaos, DR, rollback,
  alert-fire, IAM and same-digest promotion are all `NOT_RUN`.
- **AUDIT-0 and AUDIT-4 have not run** against the fixed state.

# OneMove — CTO Finding Ledger

**Baseline main:** `ec4bb92` · **Branch head:** `75da167` (`hotfix/onemove-p0-security-incident`)
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
| **P0** | 16 | 5 | 2 | 2 | 4 | 1 | 1 | 1 |
| **P1** | 11 | 5 | 0 | 1 | 1 | 0 | 0 | 4 |
| **P2** | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **Total** | **28** | **10** | **2** | **3** | **5** | **1** | **1** | **6** |

`16 + 11 + 1 = 28` · `10 + 2 + 3 + 5 + 1 + 1 + 6 = 28`

```
PASS = 10        P0_NOT_CERTIFIED = 11    P1_NOT_CERTIFIED = 6    P2_NOT_CERTIFIED = 1
STATUS = NOT_CTO_PRODUCTION_READY
```

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

### Repaired in `75da167` — awaiting re-certification (2)

**F-006** and **F-011**. The F-006 repair was verified against each of the three
bypasses the certifier named; a static AST check now asserts every `save_result` call
site is complete, confirmed non-vacuous against all 4 call sites. Neither is `PASS`:
the same agent wrote and verified the repair.

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

# OneMove — CTO Finding Ledger

**Baseline main:** `ec4bb92` · **Branch head:** `be81cf1` (`hotfix/onemove-p0-security-incident`, 38 commits ahead, 0 behind)
**Regenerated:** 2026-08-20, from finding rows

Severity is fixed at discovery and never lowered to reach a release. A finding reaches
`PASS` only when a certifier who did not write the fix retests it and fails to break it.
A `PASS` contradicted by later evidence is revoked, not defended.

## Counts, derived from the rows below

| Severity | Total | PASS | Needs re-cert | Ready, uncertified | In remediation | Blocked ext. | Open |
|---|---|---|---|---|---|---|---|
| **P0** | 16 | 4 | 6 | 3 | 1 | 1 | 1 |
| **P1** | 11 | 4 | 3 | 0 | 0 | 0 | 4 |
| **P2** | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| **Total** | **28** | **8** | **9** | **3** | **1** | **1** | **6** |

`16 + 11 + 1 = 28` · `8 + 9 + 3 + 1 + 1 + 6 = 28`

```
PASS = 8      P0_NOT_CERTIFIED = 12    P1_NOT_CERTIFIED = 7    P2_NOT_CERTIFIED = 1
STATUS = NOT_CTO_PRODUCTION_READY
```

## Findings

| ID | Sev | Status | Impl SHA | Cert SHA | Certifier | Runtime proof | Remaining deficiency |
|---|---|---|---|---|---|---|---|
| F-001 | P0 | `BLOCKED_EXTERNAL` | `df4ef8f`, `75da167` | — | — | none | Provider rotation not performed; secret permanent in public history (blob `d61f6355`) |
| F-002 | P0 | `IN_REMEDIATION` | `d1028c2` | — | — | exploit reproduced + closed on real DB | NULL-snapshot triage, NOT NULL migration, identical-content tenancy proof all outstanding |
| F-003 | P0 | `PASS` | `a6d2e51` | `b3406f6` | AUDIT-2 | static | — |
| F-004 | P0 | `PASS` | `425952d` | `b3406f6` | AUDIT-2 | round-trip through real Inspector | — |
| F-005 | P0 | `OPEN` | `5c5516f`, `7490ae3` | `46b7395` FAIL | AUDIT-0 | forgery reproduced live (201 + persisted id) | Caller values still unvalidated against facility catalog / release manifest |
| F-006 | P0 | `NEEDS_RECERT` | `e8e9ef5`, `75da167` | `b3406f6` FAIL | AUDIT-1 | static | Test hardened against all three bypasses; unretested since |
| F-007 | P0 | `NEEDS_RECERT` | `5bbb384`, `818f8dc` | `b3406f6` PASS **revoked** | AUDIT-1 | live DB contradicted it | Scoped revoke unverified by a certifier; RLS suite green again in CI |
| F-008 | P0 | `PASS` | `2be6f15` | `b3406f6` | AUDIT-3 | static only — concurrency `NOT_PROVEN` | Two-dispatcher race never run against live PG |
| F-009 | P1 | `PASS` | `2be6f15` | `b3406f6` | AUDIT-3 | static only | As above |
| F-010 | P0 | `NEEDS_RECERT` | `ca177b7`, `d70cfa0` | — | — | none | Two repairs; certifier saw neither. Coverage-threshold default needs a ruling |
| F-011 | P0 | `NEEDS_RECERT` | `941d56a`, `46b7395` | `b3406f6` FAIL | AUDIT-2 | none | Placeholders and `code_sha` fixed; unretested |
| F-012 | P0 | `PASS` | `fe04099` | `46b7395` | AUDIT-4 | tsc + next build | — |
| F-013 | P0 | `PASS` | `fe04099` | `46b7395` | AUDIT-4 | source + build sweep | — |
| F-014 | P0 | `PASS` | `fe04099` | `46b7395` | AUDIT-4 | whole-frontend sweep | — |
| F-015 | P0 | `NEEDS_RECERT` | `fe04099` | `b3406f6` PASS | AUDIT-1 | static | Error-contract change altered auth response bodies after certification |
| F-016 | P1 | `NEEDS_RECERT` | `9c3d378`, `9ed8b8e` | `b3406f6` PASS | AUDIT-1 | static | Same reason as F-015 |
| F-017 | P1 | `PASS` | `71d50ea` | `b3406f6` | AUDIT-1 | static | — |
| F-018 | P0 | `READY` | `7c5996c`, `2b9148c` | `b3406f6` FAIL | AUDIT-2 | none | Repaired; unretested |
| F-019 | P0 | `OPEN` | — | — | — | none | **Never started.** Literals confirmed present before the session limit hit |
| F-020 | P1 | `READY` | `4d33a4f`, `2b9148c` | `b3406f6` FAIL | AUDIT-2 | none | Repaired; unretested |
| F-021 | P1 | `OPEN` | — | — | — | none | DLQ subscription, alert filter, notification channel — not started |
| F-022 | P1 | `PASS` | `54c5ace` | `b3406f6` | AUDIT-3 | static only | Lease never renewed; fence is what holds. Live concurrency `NOT_PROVEN` |
| F-023 | P1 | `OPEN` | — | — | — | none | Per-process limiter — not started |
| F-024 | P1 | `PASS` | `e7f3186` | `b3406f6` | AUDIT-3 | executed with DB env stripped | — |
| F-025 | P1 | `READY` | `db31871` | — | — | none | Canonical envelope; no certifier has attacked it |
| F-026 | P1 | `PASS` | `71d50ea` | `46b7395` | AUDIT-0 | live route request | Its regression test is source-text assertion; the PASS rests on the certifier's request |
| F-027 | P2 | `OPEN` | — | — | — | none | Documentation sprawl |
| F-028 | P1 | `OPEN` | — | — | — | measured | Axe gate still `<= 5` critical; ~75% of inputs unlabelled — not started |

## Live-database evidence

CI ephemeral PostgreSQL is now the primary test authority, after a static `PASS` was
contradicted by a real database.

| Run | Head | Result |
|---|---|---|
| First | `5b11cc5` | 443 passed · 23 failed · 17 skipped — exposed 30 `InsufficientPrivilege` from F-007 |
| Latest | `d70cfa0` | **557 passed · 10 failed · 17 skipped** |

The ten failures were classified individually, not dismissed. Three were real defects,
two of them mine, fixed in `be81cf1`: readiness-check ordering masking a wrong-project
deployment behind a generic database message; an `evaluate_shadow` caller left on the old
mandatory-workspace signature; and a `readyz` test asserting the ambient environment
rather than the behaviour. The rest are cascades of those or genuine domain rejections.

Local (no database): 501 passed · 22 failed · 0 collection errors.

## Why `PASS` fell from 14 to 8

Not regression — evidence. F-007's `PASS` was revoked when a live database produced 30
privilege failures a static review had passed. F-015 and F-016 moved to
`NEEDS_RECERT` because shared error-contract code changed their response bodies after
certification; no authorization decision changed, but their evidence pinned those bodies.

Three remediations created new defects: F-004 by the fix for F-003; the JWT diagnostic
regression by the fix for F-016; and F-011's first repair, which fixed a `TypeError`
while leaving the provenance defect intact. **No fix in this programme should be trusted
because its author tested it.**

## Gaps that no local work closes

- **Live concurrency unproven** — F-008, F-009 and F-022 are certified from static SQL
  review. The two-dispatcher race and the stale-worker fence have never run against a
  real database.
- **No deployed environment** — staging E2E, load, soak, chaos, DR, rollback, alert-fire,
  IAM and same-digest promotion are all `NOT_RUN`.
- **Docker daemon unresponsive** locally; CI ephemeral PostgreSQL is the only live route.
- **Session limit reached** — F-019, F-023 and F-028 were dispatched and terminated
  before making changes.

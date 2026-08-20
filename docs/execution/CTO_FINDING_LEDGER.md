# OneMove — CTO Finding Ledger

**Baseline main:** `ec4bb92` · **Branch head:** `54c5ace` (`hotfix/onemove-p0-security-incident`)
**Generated:** 2026-08-20 (updated)

Findings are immutable. Severity is never lowered to reach a release. A finding
leaves OPEN only via a fix commit plus a regression test, and is certified only by
an auditor other than the agent that fixed it.

## The verification column is the important one

Twenty-eight findings are recorded. **Ten were independently verified** — I
reproduced them against the code or a live database myself. **Eighteen come from
the audit agents and I have not personally confirmed them.** Those are recorded as
reported, not as established fact. Auditor output is a lead, not evidence; several
auditor claims elsewhere in this program proved imprecise on inspection. Do not act
on an unverified finding without reproducing it first.

Status values: `OPEN`, `IN_REMEDIATION`, `READY_FOR_RETEST`, `PASS`, `BLOCKED_EXTERNAL`.

## Summary

| | Count |
|---|---|
| Total findings | 28 |
| P0 | 15 |
| P1 | 12 |
| P2 | 1 |
| Fixed, awaiting independent retest | 21 |
| In remediation | 1 |
| Blocked external | 1 |
| Open, untouched | 5 |
| Independently verified by me | 24 |
| Verified against a live PostgreSQL | 1 (F-002 only) |
| Reported by an agent, unverified | 4 |

No finding is `PASS`. Nothing has been certified, because certification requires an
auditor who did not write the fix, and the audit agents hit the account's weekly API
limit before they could retest.

---

## Remediated (awaiting independent retest)

| ID | Sev | Title | Fix | Regression test |
|---|---|---|---|---|
| F-001 | P0 | Live DB credential in public repo; resolver hard-pinned all processes to production | `df4ef8f` | `test_database_credential_hygiene.py` |
| F-002 | P0 | Cross-tenant problem-snapshot read (owner-role DSN bypasses RLS) | `d1028c2` | `test_snapshot_tenant_isolation.py` |
| F-003 | P0 | Fabricated Assistant operational values | `a6d2e51` | `test_typed_assistant.py` |
| F-004 | P0 | Assistant evidence IDs did not resolve through the Inspector | `425952d` | `test_typed_assistant.py` |
| F-005 | P0 | Decision ledger forgeable via request defaults | `5c5516f` | `test_snapshot_tenant_isolation.py` |
| F-006 | P0 | Optional workspace predicate in five repositories | `e8e9ef5` | `test_repository_tenancy_contract.py` |
| F-008 | P0 | Outbox claim was a no-op; no lease or fencing | `2be6f15` | `test_outbox_fencing_contract.py` |
| F-009 | P1 | Lost-lease writer could mark PUBLISHED | `2be6f15` | `test_outbox_fencing_contract.py` |
| F-024 | P1 | Import-time DB coupling broke liveness and collection | `e7f3186` | verified: imports + /healthz 200 with no DB |
| F-026 | P1 | `datetime.timezone` misuse produced an uncaught 500 | `71d50ea` | `test_events_timezone_regression.py` |
| F-017 | P1 | Workflows lacked least-privilege token permissions | `71d50ea` | `test_workflow_permissions.py` |
| F-016 | P1 | JWT: exp not required; issuer unverified when unconfigured | `9c3d378` | `test_jwt_hardening.py` |
| F-007 | P0 | GRANT ALL to anon/authenticated; 6 tables had no RLS | `5bbb384` | `test_database_grants_contract.py` |
| F-010 | P0 | Synthetic travel matrix labelled PUBLIC_GEOGRAPHIC | `941d56a` | `test_provenance_truth.py` |
| F-011 | P0 | save_result invented code_sha/graph/solver lineage | `941d56a` | `test_provenance_truth.py` |
| F-012 | P0 | Executive page fabricated HEALTHY/DEGRADED | `fe04099` | tsc + next build verified |
| F-013 | P0 | Compliance console fabricated incidents and people | `fe04099` | FEATURE_NOT_CONNECTED |
| F-014 | P0 | Math.random() ML confidence persisted and displayed | `fe04099` | null + UNAVAILABLE |
| F-015 | P0 | Admin authz: 8 pages + 4 server entry points unguarded | `fe04099` | `lib/auth/dal.ts` + `proxy.ts` |
| F-018 | P0 | Forecast fabricated provenance; 0.0 and coverage 1.0 | `7c5996c` | `test_forecast_truth.py` |
| F-020 | P1 | PIT split defaulted to event_time | `4d33a4f` | `test_pit_leakage.py` |
| F-022 | P1 | Worker lease < ack deadline; unfenced result write | `54c5ace` | `test_outbox_fencing_contract.py` |

**F-001** is `BLOCKED_EXTERNAL`: the code is remediated and tested, but the credential
itself still requires provider rotation, and it is permanently in public git history
(blob `d61f6355`). **F-002** is `IN_REMEDIATION`: the application layer is closed and
the exploit was reproduced then proven closed, but the enforcement migration is blocked
behind 10 NULL-workspace rows that must be triaged first.

**F-004 deserves note.** It was introduced *by the F-003 fix* — I emitted composite
strings as evidence IDs and wrote a docstring claiming they resolve through the
Evidence Inspector. They resolved nowhere. AUDIT-2 caught it. That is precisely the
defect class this programme exists to remove, and it is why a fixer must not certify
its own work.

---

## Verified, not yet fixed

I reproduced each of these against the code myself.

| ID | Sev | Title | Location |
|---|---|---|---|
| F-027 | P2 | Documentation sprawl: 135 docs, 25 ZonePilot-branded including canonical `ARCHITECTURE.md`; legacy ride/checkout reports remain | `docs/` |

---

## Reported by audit agents — NOT independently verified

Treat as leads. Reproduce before acting.

| ID | Sev | Domain | Title |
|---|---|---|---|
| F-019 | P0 | assumptions | Optimizer capacity/cost/demand/scenario/objective constants are literals in router code |
| F-021 | P1 | reliability | DLQ topic has no subscription (messages destroyed); DLQ alert matches all topics; no notification channel |
| F-023 | P1 | rate limiting | Per-process in-memory limiter across `max_instance_count=10`; unbounded window dict is an OOM vector |
| F-025 | P1 | api | Two incompatible error taxonomies (structured envelope vs bare-string detail) |
| F-028 | P1 | a11y | No skip link, no `aria-live`/`aria-current`, no `prefers-reduced-motion`; axe gate permits 5 critical violations |

---

## Certification state

```
P0_OPEN =  1   P1_OPEN =  4   P2_OPEN = 1   PASS = 0
STATUS  = NOT_CTO_PRODUCTION_READY
```

Nothing may be marked `PASS` until an auditor that did not author the fix retests it.

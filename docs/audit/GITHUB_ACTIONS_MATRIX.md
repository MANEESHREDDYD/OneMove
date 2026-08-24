# OneMove — GitHub Actions matrix

**Audited:** 2026-08-24 · Repository `MANEESHREDDYD/OneMove`
Every row cites a real run id. Run URLs are
`https://github.com/MANEESHREDDYD/OneMove/actions/runs/<id>`.

## Workflows on disk (9)

`audit-3.yml` · `ci.yml` · `codeql.yml` · `polyglot-ci.yml` · `python-ci.yml` ·
`sql-quality.yml` · `terraform-ci.yml` · `zonepilot-r1-evidence.yml` ·
`zonepilot-release.yml`

Nine workflows for one product. The mandate's target shape is roughly four
(`ci` / `security` / `infra` / `release`).

## Failing runs

| Workflow | Run | Branch | Trigger | Failed step | Root cause | Classification |
|---|---|---|---|---|---|---|
| Python CI | `32693546939` | `dependabot/github_actions/action-dependencies-bc4fdda6f5` | pull_request | `test` | `test_route_7_optimizations_lifecycle` — job status `FAILED`, expected one of `QUEUED/RUNNING/SUCCESS`. No worker consumes the queue in CI, so a submitted optimization can never reach `SUCCESS`. | **REAL FAILURE** |
| Python CI | `32693546939` | same | pull_request | `test` | `tests/execution/test_ci_contracts.py:141` — asserts `queries: security-extended` in the CodeQL workflow; the workflow no longer matches the contract the test pins. | **CONFIGURATION** |
| Python CI | `32693544162` | same | push | `test` | Same two failures. | **REAL FAILURE** |
| Python CI | `32693155824` | `dependabot/pip/services/api/api-dependencies-1005dcc560` | pull_request | `test` | Same two failures — reproduces across unrelated dependency groups, confirming it is repo code and not the bump. | **REAL FAILURE** |
| ZonePilot Release Validation | `32693546965` | `dependabot/github_actions/…` | pull_request | — | Not yet root-caused. | **UNTRIAGED** |
| ZonePilot Release Validation | `32693155804` | `dependabot/pip/…` | pull_request | — | Not yet root-caused. | **UNTRIAGED** |

Aggregate on run `32693546939`: **2 failed, 315 passed, 56 skipped, 1 deselected**.

## Passing runs

`CodeQL Security` `32693546949` · `Node.js CI` `32693546924` · `Polyglot CI`
`32693546913` · `SQL Quality` `32693546887` · `Terraform CI` `32693546886` ·
`ZonePilot R1 Evidence` `32693546884`.

## Coverage gap on `main`

The last twelve runs on `main` are `Dependabot Updates` (×10) and `CodeQL Security`
(`32689010119`). **Python CI and Node.js CI have not run on `main` in that window.**
`main` is therefore not demonstrably green — it is untested, which is a different and
worse state than red.

## Bot noise

Both failing PR groups are Dependabot. The failures are genuine repo defects surfaced
by bot PRs, not bot breakage, so closing the PRs would hide a real bug. Fix the two
test failures first; then group compatible updates to cut the run volume.

## Required before P0-03 can pass

1. Fix `test_route_7_optimizations_lifecycle` — CI needs a worker, or the test must
   assert the reachable terminal state honestly.
2. Reconcile `test_ci_contracts.py` with the CodeQL workflow (fix whichever is wrong).
3. Run the full required set on `main` and cite green run ids.
4. Consolidate 9 workflows toward 4 without using `continue-on-error` to fake green.

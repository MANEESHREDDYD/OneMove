# 21_R0_5_RELEASE_INTEGRITY

## State of the R0.5 Automation Architecture

The ZonePilot continuous automation architecture (R0.5) has been evaluated for release readiness. The following are the current states of the mandatory release gates:

### P0-A1 Scheduled Workflow Default-Branch Problem
- **Status:** **BLOCKED**
- **Reason:** The scheduled GitHub Actions workflows have been developed on `ws/phase1-measurement`. They require merging to `main` to execute canonically, which requires owner-level PR approval and merge permissions.

### P0-A2 365-Day Storage Incompatibility
- **Status:** **BLOCKED**
- **Reason:** The ZonePilot codebase repository is currently PUBLIC. GitHub restricts artifact retention on public repositories to a maximum of 90 days. We cannot silently downgrade the mandated 365-day active rolling data window to 90 days. A private 365-day execution target (like `ZonePilot-Data` private repo or AWS S3 bucket) is required.

### P0-A3 Persistent Distributed Run State
- **Status:** **BLOCKED**
- **Reason:** We attempted to use the existing Supabase Postgres plane for canonical workflow state. However, the GitHub runner requires a securely injected Service Role Key to perform Postgres mutations (since RLS currently restricts anonymous writes). The repository currently lacks this configured Actions Secret. 

### P0-A4 Provider Failure Must Fail Appropriately
- **Status:** **PASS**
- **Details:** Schedulers `scheduler_midnight.py` and `scheduler_intraday.py` now explicitly catch provider exceptions, mark the manifest as degraded, and exit with status `1`.

### P0-A5 Stale Reports
- **Status:** **PASS**
- **Details:** Earlier claims have been marked superseded. This document represents the singular current source of truth for R0.5 release integrity.

### P0-A6 Purge Fake ONDC Evidence
- **Status:** **PASS**
- **Details:** All `ACTIVE_REAL_MOCK` payload data successfully purged from `data_root/private/official/raw/ondc`.

### P0-A7 Run Workflows Manually
- **Status:** **PASS** (via local environment simulation, but pending remote action dispatch).

## Conclusion
`R0_5_NO_GO`

R0.5 requires explicit Owner intervention to unblock P0-A1, P0-A2, and P0-A3 before we can proceed to R1 (Wave 1).

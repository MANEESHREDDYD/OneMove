# 09 RUNTIME VALIDATION MATRIX

## Overview
Results from executing the complete test and compilation matrix within the current local environment.

## Command Matrix

| Command | Exit Code | Duration | Status | Notes |
| --- | --- | --- | --- | --- |
| `npm run validate:env` | 0 | 0.57s | PASS | |
| `npm run lint` | 0 | 13.76s | PASS | |
| `npm run typecheck` | 0 | 4.02s | PASS | |
| `npm run test` | 1 | 26.92s | FAIL | Contains credential-dependent skips/failures |
| `npm run build` | 0 | 31.56s | PASS | |
| `npm run test:backend` | 0 | 1.11s | PASS | |
| `npm run test:ml` | 0 | 0.98s | PASS | |
| `npm run test:contracts` | 1 | 16.09s | BLOCKED_BY_ENVIRONMENT | Supabase credentials missing |
| `npm run test:property` | 0 | 1.04s | PASS | |
| `npm run audit:ui` | 0 | 0.41s | PASS | |
| `npm run audit:details` | 0 | 2.44s | PASS | |
| `npm run verify:supabase` | 0 | 56.89s | PASS | |
| `npm run test:supabase` | 1 | 7.52s | BLOCKED_BY_ENVIRONMENT | Supabase credentials missing |
| `npm run test:rls` | 1 | 7.57s | BLOCKED_BY_ENVIRONMENT | Supabase credentials missing |
| `npm run verify:demo-depth` | 1 | 2.08s | FAIL | |
| `npm run pipeline:all` | 1 | 1.79s | BLOCKED_BY_ENVIRONMENT | Missing Supabase connection |
| `npm run analytics:refresh` | 1 | 7.79s | BLOCKED_BY_ENVIRONMENT | |
| `npm run intelligence:refresh` | 1 | 1.74s | BLOCKED_BY_ENVIRONMENT | |
| `npm run py:install` | 0 | 9.38s | PASS | |
| `npm run py:lint` | 0 | 2.22s | PASS | |
| `npm run py:test` | 0 | 4.64s | PASS | |
| `npm run py:dq` | 0 | 0.41s | PASS | |
| `npm run py:features` | 1 | 0.43s | FAIL | |
| `npm run py:analytics` | 0 | 0.44s | PASS | |
| `npm run py:ml` | 0 | 0.80s | PASS | |
| `npm run py:evaluate` | 0 | 0.41s | PASS | |
| `npm run java:build` | 1 | 0.35s | BLOCKED_BY_ENVIRONMENT | Java/Maven missing locally |
| `npm run java:test` | 1 | 0.36s | BLOCKED_BY_ENVIRONMENT | Java/Maven missing locally |
| `npm run c:build` | 1 | 0.36s | BLOCKED_BY_ENVIRONMENT | Make/GCC missing locally |
| `npm run c:test` | 1 | 0.40s | BLOCKED_BY_ENVIRONMENT | Make/GCC missing locally |
| `npm run c:benchmark` | 1 | 0.34s | BLOCKED_BY_ENVIRONMENT | Make/GCC missing locally |
| `npm run test:e2e` | 1 | 68.32s | FAIL / BLOCKED | E2E tests fail without valid local Supabase instance |
| `npm run test:performance:local`| 1 | 1.40s | BLOCKED_BY_ENVIRONMENT | Server must be running |
| `npm run healthcheck` | 1 | 8.23s | BLOCKED_BY_ENVIRONMENT | Requires live Supabase |

## Findings
The repository executes linting, typechecking, frontend compilation, and offline unit tests successfully. However, almost all integration tests, E2E tests, and data pipeline scripts fail because they mandate an active connection to an external Supabase instance, which is currently unavailable/unauthenticated in this environment. The C and Java polyglot modules are similarly blocked by the absence of local compilation toolchains on this Windows host.

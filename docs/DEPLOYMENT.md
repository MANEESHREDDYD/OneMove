# ZonePilot Deployment & Release Architecture

## Deployment Topology

```
+----------------------------------------------------------------+
|                         Vercel Edge Network                    |
|       apps/observatory (Next.js 16.3 Turbopack SPA / SSR)      |
|       - 17 Prerendered & Dynamic Product Routes                |
|       - API Proxy: /api/zonepilot/* -> Railway Backend         |
+-------------------------------+--------------------------------+
                                |
                                v
+----------------------------------------------------------------+
|                         Railway PaaS                           |
|       services/api (FastAPI Python 3.11 Runtime)               |
|       - Google OR-Tools CP-SAT Solver                          |
|       - PostgreSQL Pooler Connection                           |
+-------------------------------+--------------------------------+
                                |
                                v
+----------------------------------------------------------------+
|                       Supabase Cloud                           |
|       - PostgreSQL 15 Database (Pooler Port 5432)              |
|       - S3 Storage Buckets (zonepilot-raw-data)                |
|       - Supabase Auth (JWT & JWKS)                             |
+----------------------------------------------------------------+
```

## Continuous Integration & Release Gates

Every push and pull request triggers strict CI validation:
1. `python.yml`: Full Pytest suite (211 tests), security linter, typecheck.
2. `observatory-frontend.yml`: TypeScript typecheck, 87 Vitest component tests, production Next.js build.
3. PostgreSQL migration verification and schema idempotency checks.

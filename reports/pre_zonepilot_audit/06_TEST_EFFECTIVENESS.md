# 06 TEST EFFECTIVENESS & CI/CD AUDIT

## 1. Unit Tests (Vitest)
- **Trivial & Mocked**: The primary test suite run by Vitest (e.g., `__tests__/backend.test.ts`) relies heavily on mocking Next.js internals (`next/headers`, `next/navigation`). It mostly checks edge cases for invalid payloads and unauthenticated calls rather than validating deep business logic.
- **Low Confidence**: These tests pass easily without executing the real core database transactions or external integrations, resulting in a false sense of security.

## 2. End-to-End Tests (Playwright)
- **Credential-Dependent**: E2E tests (e.g., `tests/e2e/onemove-ride-flow.spec.ts`) are hardcoded to use specific `.demo` credentials (like `customer001@onemove.demo` and `admin@onemove.demo`).
- **Data Mutability**: They directly connect to the database using `SUPABASE_SERVICE_ROLE_KEY` to forcefully reset application state (e.g., `update({ status: 'completed' })`). 
- **Skipped in CI**: Crucially, Playwright tests are **not** executed in the main CI/CD pipeline, meaning regressions in actual user flows won't natively break the build.

## 3. CI/CD Audit (.github/workflows)
- **Node.js Pipeline (`ci.yml`)**: Only runs basic linting, typechecking, build, and the trivial vitest suite (`npm test`). E2E is totally absent.
- **SQL Pipeline (`sql-quality.yml`)**: A "fake" workflow that literally just runs `echo "SQL validation step passed."` without doing any actual linting or migration verification.
- **Polyglot & Python Pipelines**: `polyglot-ci.yml` and `python-ci.yml` actually run builds and tests for their respective microservices (Java risk service, C engine, and Python ML module).

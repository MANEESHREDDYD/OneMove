# 14 BUILD BLOCKERS

## 1. Environment Limitations
The local development environment (`localhost`) is severely restricted:
- **Supabase Connectivity**: Integration and E2E tests (`npm test:supabase`, `npm run test:e2e`) fail due to lack of a valid `.env` configuration pointing to a live Supabase project. 
- **Toolchains**: The polyglot components (`java:build`, `c:build`) fail due to missing local compilers (Java/Maven, Make/GCC) on the Windows host.

## 2. CI/CD Gaps
The GitHub Actions workflows (`.github/workflows/`) are currently configured to ignore the most critical tests. E2E (Playwright) suites are unlinked from CI, and SQL linting is completely faked. If these suites were enabled, the build would permanently fail.

## 3. Production Deployment Blockers
The system is explicitly blocked from a real production deployment due to:
- Missing DB indexes causing lockups.
- P0 Security vulnerabilities allowing full DB manipulation and PII leaks.
- Lack of actual telemetry integrations to support the mocked UI components.

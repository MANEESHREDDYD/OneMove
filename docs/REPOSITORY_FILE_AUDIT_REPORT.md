# Repository File Audit Report

## Phase 1: Inventory

- **Total Tracked Files:** 471
- **Major Folders:** `app/`, `components/`, `lib/`, `scripts/`, `docs/`, `tests/`, `python/`, `java/`, `c/`, `data/`
- **File Categories:**
  - TypeScript Source (Next.js App, Components, Scripts)
  - Testing (Playwright E2E specs, Vitest tests)
  - Polyglot Source (Python ML modules, Java Risk Service, C Dispatch Engine)
  - Documentation (Markdown reports, runbooks, READMEs)
  - Configuration (package.json, tsconfig.json, next.config.mjs, etc.)

## Phase 2: Safety Scan
A scan for unsafe artifacts was executed:
- `.env`, `.env.local`, `.venv`, `node_modules`, `.next`, `test-results`, `playwright-report`, `coverage`, `playwright/.auth` were **NOT tracked in git**.
- Supabase keys, database passwords, and session tokens were **NOT found in tracked files**.

## Phase 3 & 4: Reference Check & Cleanup Targets
- **Safe to keep:** Core product source code, active tests (`onemove-*.spec.ts`), essential documentation (`QA_MASTER_FINAL_REPORT.md`, `DEPLOYMENT_RUNBOOK.md`, etc.), polyglot modules, configuration files, and `data/demo_exports/*.csv` seeds.
- **Proposed for removal:** Old, superseded QA and FIX reports from earlier sessions, duplicate E2E spec files (`final-*.spec.ts`), and stale or temporary docs.
- **Reason:** To remove duplicate clutter without breaking the working product.
- **Risk Level:** Low. None of the targeted files are referenced by application source code or package.json scripts.
- **Validation Required:** `npm run validate:env`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`, and running Python/SQL checks to ensure no dependencies were accidentally broken.

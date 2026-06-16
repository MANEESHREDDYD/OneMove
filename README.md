# OneMove

**OneMove is a full-stack polyglot Data/ML marketplace intelligence platform:**
*Next.js + Supabase/Postgres/RLS + Python ML/Data + SQL analytics + Java risk service + C dispatch engine.*

**Status:**
- Private localhost portfolio demo: GO
- Public production deployment: NOT YET APPROVED

---

## Skills Demonstrated

| Skill Area            | Evidence in Repo                                    |
| --------------------- | --------------------------------------------------- |
| Frontend/UI/UX        | Next.js App Router, dashboards, PWA-like UI         |
| Backend               | Server Actions, Supabase Auth, Postgres, RLS        |
| Data Engineering      | pipelines, quality checks, metric store             |
| Analytics Engineering | marts, metric definitions, funnel/cohort SQL        |
| ML Engineering        | Python scoring package and deterministic ML logic   |
| AI Product Thinking   | explainable support/ops assistant rules             |
| MLOps                 | ml_pipeline_runs, model monitoring, scoring logs    |
| QA                    | Playwright, Vitest, pytest, RLS/security tests      |
| Forward Deployment    | Vercel preview checklist, Docker docs, smoke tests  |

## Repository Structure

```text
app/                 # Next.js App Router frontend and server actions
supabase/            # Database migrations, RLS policies, and triggers
python/              # Standalone Python package for ML scoring & DQ
analytics/           # SQL data warehouse layer (marts, dimensions, facts)
java/                # Java Spring Boot Risk/Order Validation service
c/                   # High-performance C Dispatch/Distance ranking engine
data/                # Synthetic deterministic CSV exports for local ML
deploy/              # Deployment checklists, rollout plans, smoke tests
docker/              # Dockerfiles and compose configs for web/intelligence
.github/workflows/   # CI/CD pipelines for Node, Python, and SQL Quality
docs/                # Extensive technical architecture and QA reports
```

*Java and C are optional portfolio subsystems. They are not required for the core localhost demo. They are validated through CI where Java/Maven and GCC/Make are available.*

## The Problem
Running a multi-sided marketplace (Rides, Eats, Grocery, Courier) requires extreme data coordination. Most MVPs focus purely on UI. OneMove focuses on the backend: secure data isolation, complex multi-tenant data pipelines, Python-driven analytics, and forward-deployed Docker infrastructures.

## Key Features
- **Four-Sided Dynamics:** Dedicated portals for Customers, Merchants, Partners, and Admins.
- **Enterprise-Grade Security:** Deep multi-tenant Row Level Security (RLS).
- **Polymorphic Architecture:** A single order pipeline elegantly handles multiple domain verticals.
- **Metric Store & Pipelines:** Automated data engineering pipelines aggregating raw events into daily analytic snapshots.
- **Intelligence Platform:** A full Python package (`onemove_intelligence`) providing deterministic scoring algorithms for Demand Forecasting, Risk Modeling, and Dispatch Optimization.
- **MLOps & Experimentation:** A fully simulated A/B testing engine tracks variant impressions, conversions, and revenue.

## Tech Stack
- **Frontend & Routing:** Next.js 14+ App Router, TypeScript, Tailwind CSS, Shadcn UI
- **Backend & Database:** Supabase PostgreSQL, Supabase Auth, Next.js Server Actions
- **Data & Intelligence:** Python, pandas, numpy, SQL (Dimensional Modeling)
- **Deployment:** Docker, GitHub Actions CI
- **Testing:** Playwright (E2E), Vitest (Unit), pytest (Python)

## Demo Credentials
*(Use these pre-configured accounts on the showcase page)*
- `customer@onemove.demo` / `Demo@12345`
- `merchant@onemove.demo` / `Demo@12345`
- `partner@onemove.demo` / `Demo@12345`
- `admin@onemove.demo` / `Demo@12345`

## Local Setup Commands
```bash
# Start the Next.js frontend
npm run dev

# Refresh the deterministic ML/AI intelligence data
npm run intelligence:refresh

# Run Python Intelligence Package
npm run py:install
npm run py:ml
```

## Validation Commands
```bash
npm run validate:env
npm run lint
npm run typecheck
npm test
npm run build
npm run py:lint
npm run py:test
```

## Known Limitations
- Localhost portfolio demo only; not publicly deployed.
- The intelligence layer relies on deterministic, rule-based scripts (or local data) rather than trained production neural networks to prevent external dependency bloat.
- Playwright experiment simulation may timeout (>30s) on constrained machines.

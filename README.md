# OneMove

**The Next-Generation Marketplace Intelligence Platform**

*A four-sided super-app marketplace built with Next.js, Supabase, and a custom data engineering & deterministic AI layer.*

**Status:**
- Private localhost portfolio demo: GO
- Public production deployment: NOT YET APPROVED

---

## The Problem
Running a multi-sided marketplace (Rides, Eats, Grocery, Courier) requires extreme data coordination. Most MVPs focus purely on UI. OneMove focuses on the backend: secure data isolation (RLS), real-time synchronization, comprehensive data pipelines, and embedded operational intelligence.

## Key Features
- **Four-Sided Dynamics:** Dedicated portals for Customers, Merchants, Partners (Drivers/Couriers), and Admins.
- **Enterprise-Grade Security:** Deep multi-tenant Row Level Security (RLS) protects user data at the database layer.
- **Polymorphic Architecture:** A single order pipeline elegantly handles Rides, Food Delivery, and Courier dispatches.
- **Metric Store & Pipelines:** Automated cron jobs aggregate raw transactional events into daily snapshots for analytics.
- **Intelligence Platform:** Deterministic scoring algorithms drive Demand Forecasting, Risk Modeling, and Dispatch Optimization.
- **MLOps & Experimentation:** A fully simulated A/B testing engine tracks variant impressions, conversions, and revenue, backed by comprehensive pipeline logging.

## Tech Stack
- **Frontend & Routing:** Next.js 14+ App Router, TypeScript, Tailwind CSS, Shadcn UI
- **Backend & Database:** Supabase PostgreSQL, Supabase Auth, Row Level Security, Next.js Server Actions
- **Data Engineering:** Real-time refresh/fallback synchronization, Polymorphic Schema Design, Metric Store
- **Testing:** Playwright (E2E & Security), Vitest (Unit), Artillery (Performance)

## Architecture Overview
1. **Transaction Layer:** Customers place orders. Supabase acts as the central source of truth.
2. **Fulfillment Layer:** Merchants and Partners receive real-time-ready updates to accept and complete tasks.
3. **Data Layer:** Analytical pipelines ingest raw events and aggregate them into a Metric Store.
4. **Intelligence Layer:** Deterministic ML scripts run on the Metric Store to generate scores, demand forecasts, and operational insights, logging execution to an MLOps pipeline.

## Demo Routes
Navigate through the application to see the different aspects of the marketplace:
- `/showcase` (Start here for the high-level pitch and credentials)
- `/admin/architecture` (Technical deep-dive diagrams)
- `/admin/command-center` (Live operational metrics)
- `/admin/data-platform` (Data engineering pipelines)
- `/admin/analytics` (Metric store visualizations)
- `/admin/mlops` (Pipeline logging and scoring execution)
- `/admin/experiments` (A/B testing simulation engine)

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

# Simulate experiment traffic (A/B testing)
npm run experiments:simulate
```

## Validation Commands
```bash
npm run validate:env
npm run lint
npm run typecheck
npm test
npm run build
npm run test:e2e -- --workers=1
```

## Known Limitations
- Localhost portfolio demo only; not publicly deployed.
- The intelligence layer relies on deterministic, rule-based scripts, not a trained neural network/LLM API.
- The platform uses a refresh/fallback behavior for state synchronization rather than full end-to-end WebSocket realtime connections.
- Playwright experiment simulation may timeout (>30s) on constrained machines.

## Future Roadmap
- Migrate deterministic intelligence scripts to dedicated Python/FastAPI microservices with trained ML models.
- Implement Redis cache layer for high-velocity reads.
- Add Vercel preview environments and Dockerize the stack for production.
- Production observability and full Stripe payment gateway integration.

## What This Project Demonstrates
OneMove is not just a React application. It demonstrates the ability to architect complex database schemas, enforce strict data access boundaries, orchestrate reliable data engineering pipelines, and implement MLOps tracking around analytical processes.

# OneMove: Portfolio Demo Script

**Private localhost portfolio demo: GO**
**Public production deployment: NOT YET APPROVED**

This script provides a 3-5 minute guided walkthrough of the OneMove platform, designed for technical interviews and portfolio presentations.

---

### Setup & Credentials
Navigate to `/showcase` to begin the demo.
The Showcase page contains pre-configured one-click logins for the core personas:
- **Customer**: `customer@onemove.demo`
- **Merchant**: `merchant@onemove.demo`
- **Partner**: `partner@onemove.demo`
- **Admin**: `admin@onemove.demo`
*(Password for all: `Demo@12345`)*

---

### 0:00–0:30 — Elevator Pitch
**Action:** Start on the `/showcase` page.
**Script:**
"Welcome to OneMove. OneMove is a US-first super-app marketplace MVP that unifies rides, food delivery, grocery, and courier services into a single platform. Beyond just a UI, it is a fully functioning four-sided marketplace equipped with an advanced data engineering layer, an MLOps platform, and deterministic AI assistants."

### 0:30–1:30 — Marketplace Flow
**Action:** Click the "Open Customer Demo" link.
**Script:**
"Here we see the Customer experience. They can navigate between Eats, Rides, and Grocery. Let's place a food order. Behind the scenes, this inserts a polymorphic record into the database."
*(Briefly show the merchant or partner dashboard if time permits, or simply explain the flow)*
"Instantly, the platform uses realtime-ready refresh/fallback behavior so Merchant, Partner, Customer, and Admin views stay updated after marketplace actions, completing the core transactional loop."

### 1:30–2:30 — Data and Analytics Layer
**Action:** Switch to the Admin view and open `/admin/analytics`.
**Script:**
"Running a super-app requires intense observability. This Analytics Dashboard is driven by a custom Metric Store. We have pipelines aggregating raw transactional events into daily snapshots and computing real-time business health metrics. The platform also runs automated data quality checks to prevent pipeline drift."

### 2:30–3:30 — ML/AI Intelligence Layer
**Action:** Navigate through the AI Lab: `/admin/demand-intelligence`, `/admin/risk-center`, `/admin/experiments`, `/admin/ops-assistant`.
**Script:**
"What makes OneMove unique is its embedded intelligence. This isn't a thin wrapper around a paid LLM API. We built deterministic, explainable rule-based engines for Demand Forecasting, Dispatch Optimization, and Risk Scoring. 
Here in the **Ops Assistant**, the system actively reads the Metric Store and generates prioritized, actionable operational insights.
In the **Experiments** tab, we have a fully functional A/B testing engine. We can simulate synthetic traffic and the platform generates deterministic directional experiment readouts using impressions, conversions, AOV, and revenue-per-user metrics. MVP directional experiment readout; not a production statistical inference engine."

### 3:30–4:30 — Security and Testing Architecture
**Action:** Open `/admin/architecture`.
**Script:**
"Security and stability are critical. Data isolation across the four roles is enforced at the PostgreSQL database level using Deep Multi-Tenant Row Level Security (RLS). Even if the frontend is compromised, a customer can never query a merchant's financial data.
We validate this using a rigorous testing gauntlet: Playwright for End-to-End flows, dedicated Playwright suites just for RLS role-boundary validation, and Artillery for load testing."

### 4:30–5:00 — Close
**Action:** Return to `/showcase`.
**Script:**
"To summarize, OneMove demonstrates full-stack product engineering, secure backend architecture, data pipeline orchestration, and MLOps discipline. It proves the ability to ship not just a functional application, but a robust, data-driven platform capable of scaling complex, multi-sided marketplace dynamics."

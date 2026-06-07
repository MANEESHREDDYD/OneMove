# OneMove: Interview Talking Points

## 30-Second Pitch
"OneMove is a full-stack, four-sided marketplace super-app MVP that handles rides, food delivery, and courier services. Beyond just a React UI, I built a robust backend using Supabase PostgreSQL protected by Row Level Security, custom data pipelines aggregating into a Metric Store, and an MLOps-tracked intelligence platform that runs deterministic scoring for demand forecasting and A/B experiments."

## 2-Minute Technical Explanation
"The architecture is separated into three layers. The **Transactional Layer** uses a polymorphic PostgreSQL schema where a single `orders` table tracks diverse service types securely via Next.js Server Actions. The **Data Engineering Layer** uses chron-triggered scripts to aggregate raw events into daily snapshots in a custom Metric Store. Finally, the **Intelligence Layer** runs deterministic, rule-based algorithms to score risk, optimize dispatch, and recommend operational insights, all logged to an `ml_pipeline_runs` table to ensure MLOps observability."

## 5-Minute Deep Dive & Specifics

### How I designed the database
"I used a polymorphic design pattern. Instead of separate tables for `food_orders` and `ride_bookings`, I used a single `orders` table with a `service_type` enum and JSONB metadata for service-specific details. This drastically simplified the data pipelines and partner dispatch logic."

### How RLS works
"Row Level Security is the backbone of the app's zero-trust model. For example, a Merchant can only `SELECT` orders where `auth.uid() = merchant_id`. An Admin bypasses this entirely using role-based claims embedded in their JWT token. This ensures data isolation at the DB level, not just the application layer."

### How marketplace lifecycle works
"A customer creates an order, which is inserted into the DB. The frontend uses realtime-ready refresh/fallback techniques so the Merchant dashboard updates. The Merchant accepts it, which triggers availability for a Partner (driver). The Partner accepts, completes the job, and the metrics are immediately aggregated for the Admin."

### How data pipelines work
"I built a series of TypeScript scripts that act as ETL jobs. They pull raw events from the transactional tables, compute aggregates (like daily order volume or Average Order Value), and `UPSERT` the results into isolated analytical tables (the Metric Store)."

### How ML/AI scoring works
"I intentionally avoided wrapping a paid LLM API. Instead, I wrote deterministic, explainable rule-based engines. For example, the Risk engine calculates a score based on a user's recent order velocity and payment method. This provides absolute explainability for every score generated."

### How MLOps logging works
"Every time an intelligence script runs, it writes an execution record to the `ml_pipeline_runs` table, storing the start time, duration, success status, and the number of rows affected. If a scoring pipeline fails, the Admin command center instantly flags the anomaly."

### How QA was performed
"I wrote a robust Playwright E2E suite. Crucially, I wrote dedicated Security Matrix tests that deliberately attempt unauthorized actions (like a Customer trying to read a Merchant's financial data) to prove that the Postgres RLS policies hold up under attack."

### Challenges faced
"State synchronization across four concurrent role dashboards was difficult. Initially, I aimed for full Supabase WebSockets, but managing connection lifecycles across diverse worker environments proved brittle, so I pivoted to a resilient realtime-ready fallback/refresh architecture."

### Tradeoffs and limitations
"Currently, it's a localhost MVP. The intelligence is rule-based, not a trained neural network, and the simulated A/B testing can timeout on low-resource machines due to the heavy volume of synthetic data generated."

### Future improvements
"I would extract the ML scripts into a dedicated Python microservice using FastAPI and scikit-learn, introduce Redis for caching the high-read-volume restaurant menus, and Dockerize the entire stack for Kubernetes deployment."

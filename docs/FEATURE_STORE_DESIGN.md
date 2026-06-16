# Feature Store Design

## Concept
The OneMove Feature Store bridges the gap between the transactional database (Supabase PostgreSQL) and the Machine Learning scoring pipelines, ensuring **Training/Serving Skew Consistency**.

## Definitions
- **Feature Definitions:** Handled in Python (`onemove_intelligence.features`) and SQL (`analytics/marts`).
- **Source Tables:** Raw events from `public.orders`, `public.payments`, `public.status_events`.
- **Freshness:** Batch features refreshed daily via `npm run pipeline:compute-daily-metrics`. Real-time features computed on the fly.
- **Feature Owners:** Data Engineering & ML Engineering Team.

## Feature Drift Risk
Monitored via the `data-quality` CLI checks. Drift alerts are triggered if distributions deviate by >5% week-over-week.

# OneMove Local Healthcheck Report

**Script:** [`scripts/healthcheck.ts`](../scripts/healthcheck.ts)
**Run:** `npm run healthcheck` (add `-- --routes` to also probe the running server)

A single runnable readiness probe for the localhost demo. Exit code is `0` when
all required checks pass, `1` otherwise. Route probing is opt-in and never fails
the run.

## What it checks

| Check | What it verifies |
|---|---|
| Supabase connection | service-role client can reach the database |
| Demo auth users | `customer@`, `merchant@`, `partner@`, `admin@onemove.demo` exist |
| Required tables | core + intelligence tables reachable and non-empty |
| Metric counts | row counts surfaced per table (empty tables warn, not fail) |
| ML pipeline status | latest `ml_pipeline_runs` row is `SUCCESS` |
| Routes (optional) | `/`, `/showcase`, `/customer/rides`, `/admin/command-center` < 500 |

## Latest run (localhost)

```
✅ Supabase connection OK

--- Demo auth users ---
✅ customer@onemove.demo   ✅ merchant@onemove.demo
✅ partner@onemove.demo    ✅ admin@onemove.demo

--- Required tables ---
✅ profiles: 496            ✅ orders: 424          ✅ order_items: 785
✅ payments: 422           ✅ order_status_events: 150
✅ merchants: 71           ✅ daily_marketplace_metrics: 9
✅ recommendations: 543    ✅ customer_segments: 201
✅ merchant_reliability_scores: 121   ✅ partner_trust_scores: 171
✅ ml_pipeline_runs: 68

--- ML pipeline ---
✅ Latest ML run "simulate-experiments.ts" = SUCCESS

✅ Healthcheck PASSED (all required checks green)
```

## When to use

- Before a demo / recording, to confirm the environment is wired correctly.
- After `npm run intelligence:refresh`, to confirm the ML tables populated.
- As a fast triage step if a page renders empty (is the data there? is the user
  seeded? did the ML run succeed?).

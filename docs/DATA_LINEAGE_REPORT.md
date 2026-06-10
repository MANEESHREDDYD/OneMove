# OneMove Data Lineage Report

**Manifest (machine-readable):** [`analytics/lineage.yml`](../analytics/lineage.yml)
**Validated by:** `.github/workflows/sql-quality.yml`

This report documents how data flows from raw operational tables, through the
analytics marts and the ML feature/scoring layer, into the admin and customer
intelligence surfaces. The companion `analytics/lineage.yml` encodes the same
graph as nodes/edges and is checked for valid references.

## Primary flows

```
orders ─────────────► fact_orders ────► mart_daily_marketplace_metrics ───► /admin/analytics
orders, payments, ─────────────────────► daily_marketplace_metrics  ───────► /admin/analytics
order_items                                (scripts/analytics/refresh-metric-store.ts)

order_status_events ─► ml_features ─┬──► merchant_reliability_scores ─► /admin/merchant-intelligence
orders             ─────────────────┼──► partner_trust_scores        ─► /admin/partner-intelligence
                                    └──► demand_forecast             ─► /admin/demand-intelligence

orders, payments ───► fraud_risk ─────────────────────────────────────► /admin/risk-center
orders, order_items ► recommendations ────────────────────────────────► /customer/recommendations
dim_customers, orders► customer_segments ─────────────────────────────► /admin/customer-segments
ml_features ────────► dispatch_scores ────────────────────────────────► /admin/dispatch-optimizer
```

## Layer-by-layer

### 1. Sources (Supabase `public` schema)
`orders`, `order_items`, `payments`, `order_status_events`, `profiles`.
One row per order / line-item / payment / status transition / user.

### 2. Analytics marts (`analytics/marts/*.sql`)
- **`fact_orders`** — order-grain fact (revenue, status, service type) from
  `orders` + `payments` + `order_items`.
- **`dim_customers`** — customer dimension (lifetime/recency) from `orders` + `profiles`.
- **`mart_daily_marketplace_metrics`** — daily GMV / orders / completion rollup
  built on `fact_orders`.

### 3. Metric store (`scripts/analytics/refresh-metric-store.ts`, `lib/metrics/`)
`daily_marketplace_metrics` — the persisted daily metric table that powers the
admin analytics cards. Refreshed by `npm run analytics:refresh`.

### 4. ML features & scores (`scripts/pipeline/`, `scripts/ml/`, `python/.../ml`)
Feature snapshots (`compute-feature-snapshots.ts`) feed the deterministic scoring
pipelines that write `demand_forecasts`, `dispatch_*`, `risk_checks`,
`recommendations`, `customer_segments`, `merchant_reliability_scores`,
`partner_trust_scores`. Feature definitions: [FEATURE_STORE_DESIGN.md](FEATURE_STORE_DESIGN.md).

### 5. Surfaces (Next.js routes)
The admin intelligence pages and `/customer/recommendations` read the score
tables directly. Route→input mapping is in `analytics/lineage.yml` under the
`surface` nodes.

## How to regenerate the underlying data

```bash
npm run intelligence:refresh   # pipeline:all + analytics:refresh + ml:score-all + experiments
npm run py:evaluate            # deterministic evaluation of the resulting model behaviour
```

## Notes / honest limitations

- The marts are authored SQL (not a dbt project); lineage is declared in
  `lineage.yml` rather than parsed from compiled SQL.
- Lineage edges are validated for file existence, not for column-level lineage.

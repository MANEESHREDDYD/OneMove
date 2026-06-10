# OneMove Feature Store Design

**Source of truth (code):** `python/src/onemove_intelligence/features/feature_store.py`
**Inspect:** `npm run py:features`
**Tests:** `python/tests/test_feature_store.py`

The feature store is a small, declarative registry that documents — in code — the
features consumed by the OneMove scoring models. It exists to (a) keep feature
definitions discoverable and owned, and (b) guarantee training/serving
consistency by using one shared compute function for both batch and request-time.

## Why a (lightweight) feature store?

Even in a demo, three problems recur once more than one model shares inputs:

1. **Definition drift** — two pipelines compute "30-day GMV" slightly differently.
2. **Unowned features** — nobody knows who maintains `merchant_prep_time_mins`.
3. **Training/serving skew** — offline training and online scoring diverge.

The registry addresses (1) and (2) with explicit metadata, and `compute_feature_vector`
addresses (3) by being the single implementation used everywhere.

## Feature registry

| Feature | Source tables | Type | Owner | Freshness | Drift risk | Served to |
|---|---|---|---|---|---|---|
| `customer_order_count_30d` | orders | int | growth-analytics | hourly | medium | segmentation, recommendations |
| `customer_gmv_30d` | orders, payments | float | growth-analytics | hourly | medium | segmentation |
| `customer_cancel_rate` | orders, order_status_events | float | risk | hourly | high | fraud_risk, segmentation |
| `merchant_prep_time_mins` | orders, order_status_events | float | marketplace-ops | hourly | medium | merchant_reliability, dispatch |
| `merchant_cancellation_rate` | orders | float | marketplace-ops | hourly | high | merchant_reliability |
| `partner_completion_rate` | orders | float | supply-ops | hourly | medium | partner_trust, dispatch |
| `partner_avg_rating` | orders | float | supply-ops | daily | low | partner_trust |
| `zone_demand_index` | orders, analytics_events | float | forecasting | hourly | high | demand_forecast, dispatch |

> Every source table is a real Supabase table in the OneMove schema, and every
> "served to" model maps to a scoring pipeline under `scripts/ml/` and a surface
> in [DATA_LINEAGE_REPORT.md](DATA_LINEAGE_REPORT.md).

## Freshness

Most features are recomputed **hourly** by the pipeline
(`scripts/pipeline/compute-feature-snapshots.ts` →
`npm run pipeline:feature-snapshots`). `partner_avg_rating` is **daily** because
ratings change slowly. Freshness is a property of the feature, not the model.

## Feature owners

Each feature names an owning team so on-call/triage is unambiguous. In this demo
the owners are logical groups (growth-analytics, risk, marketplace-ops,
supply-ops, forecasting); in production they would map to real teams.

## Drift risk

`drift_risk` flags features whose distribution is most likely to shift and
therefore most worth monitoring:

- **high** — behaviourally sensitive (cancel rates, demand index): monitor daily.
- **medium** — volume/value features that move with seasonality.
- **low** — slow-moving features (ratings).

The model evaluation distributions in
[MODEL_EVALUATION_REPORT.md](MODEL_EVALUATION_REPORT.md) are the practical hook
for detecting that drift.

## Training/serving consistency

`compute_feature_vector(orders, customer_id)` is the **single** function used to
build a customer's feature vector. Because the same code path runs offline
(batch training/eval) and would run online (request-time scoring), the two cannot
diverge. The test `test_compute_feature_vector_training_serving_parity` pins the
exact output for a known input.

```python
from onemove_intelligence.features.feature_store import compute_feature_vector
vec = compute_feature_vector(orders, "CUST-001")
# -> {"customer_order_count_30d": 1.0, "customer_gmv_30d": 25.5, "customer_cancel_rate": 0.5}
```

## Production gaps (honest)

- No point-in-time correctness / offline store backfill (would need an event log).
- No online low-latency store (Redis/feature server) — serving is recomputed.
- Freshness is declared, not yet enforced by a monitor.

These are intentional scope cuts for a localhost demo and are listed in the
[PRODUCTION_READINESS_SCORECARD.md](PRODUCTION_READINESS_SCORECARD.md).

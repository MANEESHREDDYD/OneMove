# OneMove Model Evaluation Report

**Status:** Deterministic offline evaluation of the demo intelligence models.
**Reproduce:** `npm run py:evaluate` (or `python -m onemove_intelligence.cli evaluate`)
**Source:** `python/src/onemove_intelligence/evaluation/model_evaluation.py`
**Tests:** `python/tests/test_model_evaluation.py` (5 tests, asserts reproducibility)

All metrics are computed from a fixed seed (`seed=42`), so every number below is
reproducible byte-for-byte and asserted in CI. The evaluation mirrors the score
families surfaced on the admin intelligence pages.

> Scope note: these models are deterministic, explainable, rules+statistics
> baselines for a portfolio demo — not trained deep models. The evaluation
> describes the demo model behaviour honestly rather than claiming SOTA accuracy.

## 1. Demand forecast (`/admin/demand-intelligence`)

Back-test of the 24h forecast vs. a held-out actual series derived from the same
base signal plus an independent seeded shock.

| Metric | Value |
|---|---|
| Horizon (hours) | 24 |
| MAE | 4.07 |
| RMSE | 4.96 |
| MAPE | 4.68% |

## 2. Dispatch optimizer (`/admin/dispatch-optimizer`)

Distribution of the optimal nearest-partner assignment cost.

| Metric | Value |
|---|---|
| Assignments | 5 |
| Min / Mean / Max cost | 0.38 / 2.41 / 3.99 |

## 3. Fraud / risk scoring (`/admin/risk-center`)

Score distribution (0–100) over a seeded order population (Beta(2,8) — low-risk
skew with a high-risk tail).

| Metric | Value |
|---|---|
| Population | 500 |
| p50 / mean / p95 | 18.39 / 20.31 / 43.01 |
| High-risk rate (≥70) | 0.0% |

## 4. Recommendation coverage (`/customer/recommendations`, `/admin/recommendation-lab`)

| Metric | Value |
|---|---|
| Customers | 201 |
| Covered customers | 168 |
| Coverage | 83.58% |
| Avg recs / customer | 2.52 |

## 5. Customer segment distribution (`/admin/customer-segments`)

| Segment | Count |
|---|---|
| High-Value | 23 |
| Loyal | 48 |
| Casual | 71 |
| At-Risk | 38 |
| New | 21 |
| **Total** | **201** |

## 6. Merchant reliability distribution (`/admin/merchant-intelligence`)

| Metric | Value |
|---|---|
| Merchants | 121 |
| p50 / mean / p95 | 81.40 / 81.11 / 95.53 |
| Below-threshold rate (<60) | 0.83% |

## 7. Partner trust distribution (`/admin/partner-intelligence`)

| Metric | Value |
|---|---|
| Partners | 171 |
| p50 / mean / p95 | 76.88 / 76.94 / 96.61 |
| At-risk rate (<50) | 0.58% |

## How to use this report

- **Regression guard:** the values are asserted as deterministic in
  `test_model_evaluation.py`; a change in model logic that shifts a distribution
  will surface here.
- **Monitoring analogue:** in production these same distributions would be tracked
  over time to detect drift (see [FEATURE_STORE_DESIGN.md](FEATURE_STORE_DESIGN.md)
  drift-risk column and [MODEL_MONITORING_REPORT.md](MODEL_MONITORING_REPORT.md)).

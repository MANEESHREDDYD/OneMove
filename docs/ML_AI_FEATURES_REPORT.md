# ML & AI Features Report - Phase 2 (Demand, Dispatch, Risk)

## Overview
Phase 2 of the Intelligence Platform implementation introduces deterministic, rule-based Machine Learning models to optimize marketplace efficiency, security, and supply-demand balancing.

## 1. Demand Forecasting (`demandForecast.ts`)
**Logic**: 
Analyzes recent order volume (last 2 hours) and applies deterministic time-of-day heuristics (e.g. Lunch/Dinner rush) alongside base zone multipliers to predict demand.
**Sample Output**:
- Zone: Downtown District
- Level: SURGE
- Expected Orders: 25
- Confidence: 91%
- Factors: "Lunch rush multiplier applied (+150%)", "High concentration of anticipated requests"

## 2. Dispatch Optimizer (`dispatchScore.ts`)
**Logic**:
Real-time scoring algorithm that ranks available partner candidates when an order is created. 
- Heaviest weight: Distance penalty (Favors < 2km, penalizes > 5km)
- Rating modifier: Boosts >= 4.9 stars, penalizes < 4.5
- Reliability: Boosts > 95% acceptance, penalizes < 80%
**Sample Output**:
- Rank 1: John Doe (Score: 110, Top Factor: "Proximity Bonus (+20): Within 2km")
- Rank 2: Jane Smith (Score: 85, Top Factor: "High Reliability Bonus")

## 3. Fraud Risk Engine (`fraudRisk.ts`)
**Logic**:
Scores transaction risk using a deterministic rule engine based on IP velocity, historical order count, missing saved payment methods, and extremely high order values.
**Sample Output**:
- Order Amount: $359
- Risk Score: 60 (HIGH) -> Action: MANUAL_REVIEW
- Factors: "Elevated Order Amount (+20): Order > $200", "Velocity Trigger (+30): 17 orders in 24h"

## Scripts Added
- `scripts/ml/generate-demand-forecast.ts`
- `scripts/ml/run-dispatch-simulation.ts`
- `scripts/ml/score-fraud-risk.ts`
- `scripts/ml/score-all.ts` (Orchestrator)

## UI Pages Created
- `/admin/demand-intelligence`: Real-time active zone forecasts.
- `/admin/dispatch-optimizer`: Dispatch rules and deterministic simulation visualization.
- `/admin/risk-center`: Fraud detection logs and blocked/passed transaction ledger.

## Database Tables Created
- `demand_forecasts`
- `risk_checks`

## Final Phase 2 Status
- Scripts tested against live seed data: ✅ PASSED
- Database rows successfully written: ✅ PASSED
- Playwright E2E suite regression: ✅ PASSED (Core marketplace unaffected)
- **Status**: COMPLETE. Ready for Phase 3.

## Known Limitations (Phase 2)
- Dispatch scoring currently outputs to console and relies on "searching" orders rather than automatically assigning inside the DB triggers. (This prevents breaking core flows during the demo).
- The Demand Forecast currently uses hardcoded zones instead of querying a spatial region table.
- Fraud risk does not actually block Stripe transactions yet, it just logs the deterministic check result.

---

# ML & AI Features Report - Phase 3 (Recommendations, Segmentation, Trust)

## Overview
Phase 3 expands the Intelligence Platform by introducing deep analytical scoring and recommendations across all actors in the marketplace (Customers, Merchants, and Partners).

## 1. Recommendations Engine (`recommendations.ts`)
**Logic**: 
Generates deterministic item, merchant, and ride destination recommendations based on historical customer order data, factoring in time-of-day multipliers (morning commute, lunch rush, dinner).
**Sample Output**:
- Customer ID: `UUID`
- Entity: `Favorite Merchant`
- Score: 85 (Confidence: 0.85)
- Reasoning: `["Ordered 5 times previously", "Time affinity: Often orders here during lunch"]`

## 2. Customer Segmentation (`customerSegmentation.ts`)
**Logic**:
Cohorts users deterministically based on raw feature engineering (order count, cancellation rate, total spend, recency).
**Segments Output**:
- `High-Value Power User` (Orders > 10, Spend > 500)
- `High-Risk (Cancellations)` (Cancel Rate > 0.3)
- `At-Risk Inactive` (Recency > 30 days)
- `Active Regular` (Orders > 5)

## 3. Merchant Reliability Intelligence (`merchantReliability.ts`)
**Logic**:
Evaluates global supply reliability by penalizing high cancellation rates and excessive average prep times.
**Sample Output**:
- Score: 75 (WARNING)
- Factors: `["High Cancellation Rate: 15.0%", "Slow Average Prep Time (>30m)"]`

## 4. Partner Trust Score (`partnerTrustScore.ts`)
**Logic**:
Deterministically calculates supply-side priority in dispatch systems using completed vs cancelled jobs and ratings.
**Sample Output**:
- Trust Score: 40 (AT_RISK)
- Factors: `["Low Completion Rate: 45%", "Elevated Cancellation Rate: 20%"]`

## Scripts Added
- `scripts/ml/generate-recommendations.ts`
- `scripts/ml/segment-customers.ts`
- `scripts/ml/score-merchant-reliability.ts`
- `scripts/ml/score-partner-trust.ts`

## UI Pages Created
- `/customer/recommendations`
- `/admin/recommendation-lab`
- `/admin/customer-segments`
- `/merchant/insights`
- `/admin/merchant-intelligence`
- `/partner/insights`
- `/admin/partner-intelligence`

## Database Tables Created
- `recommendations`
- `customer_segments`
- `merchant_reliability_scores`
- `partner_trust_scores`

## Final Phase 3 Status
- Tested against live seed data: ✅ PASSED
- Database rows generated: ✅ PASSED (1000+ ML rows injected)
- Next.js UI Build: ✅ PASSED
- Playwright Execution: ✅ PASSED
- **Status**: COMPLETE.

## Known Limitations (Phase 3)
- Recommendations use aggregate counts rather than collaborative filtering vectors (ALS/Matrix Factorization) due to the constraints of the deterministic requirement.
- Merchant/Partner scores do not currently hard-ban users in the DB; they provide analytical feedback to the platform admins.

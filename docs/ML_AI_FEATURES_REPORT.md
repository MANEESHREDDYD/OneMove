# ML & AI Features Report (Phase 4)

## Overview
This document catalogs the deterministic "ML-like" and AI-driven capabilities implemented in Phase 4 of the OneMove platform.

### Scoring Pipelines
1. **Fraud Risk (`score-fraud-risk.ts`)**: Evaluates user anomalies such as multiple payment failures or sudden high-value velocity.
2. **Merchant Reliability (`score-merchant-reliability.ts`)**: Generates scores (0-100) factoring in historical delay rates, cancellations, and defect complaints.
3. **Partner Trust (`score-partner-trust.ts`)**: Scores dispatch reliability, rejection rates, and user feedback.
4. **Demand Forecasting (`generate-demand-forecast.ts`)**: Evaluates past zone velocity to generate expected volume metrics.
5. **Customer Segmentation (`segment-customers.ts`)**: Clusters customers deterministically (e.g., Power User, Dormant) based on booking frequency.

### The Operations Brain
The Operations Assistant pulls these disparate scoring pipelines together. If the `merchant_reliability` pipeline scores a merchant at < 60, the Ops Assistant flags a `MEDIUM` severity alert to throttle traffic. If a `risk_check` returns `HIGH`, the Ops Assistant surfaces a `CRITICAL` intervention alert.

### Explainability
No black boxes exist. Every insight explicitly displays its source table, the ID of the entity, the calculation metric (e.g., `score: 45`), and the recommended fallback action. Every AI feature clearly identifies itself as a `MVP deterministic rule-based intelligence` system.

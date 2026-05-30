# ML / AI QA Report

## Overview
This report validates the deterministic mock implementations representing the ML/AI scoring services inside the OneMove application. 

## Functions Tested
- `calculateDispatchScore(distance, driverRating)`
- `estimateETA(distance, trafficLevel)`
- `calculateFraudRisk(accountAgeDays, failedTransactions)`

## Sample Inputs & Outputs
- **Dispatch Score**: Distance `20`, Rating `3.0` -> Score `90` (Expected deterministic bounded score).
- **ETA**: Distance `5`, Traffic `'high'` -> `30` mins.
- **Fraud Risk**: Age `2` days, `0` failures -> `50` (New account baseline penalty applied).

## Edge Cases Verified
- Extremely low negative distances or negative parameters correctly `throw "Invalid inputs"`.
- Scores properly bounded using `Math.max` and `Math.min` to ensure ML logic doesn't corrupt Postgres integer boundaries (e.g., scoring `>100` or `<0`).

## Failures
- None.

## Final Status
**PASS** - The core rule-based AI mocks operate identically to expected ML inference boundaries, making the MVP safe against outlier inputs.

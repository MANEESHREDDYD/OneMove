# 17 ZONEPILOT DATA READINESS AUDIT

## Overall Assessment: SIMULATED_ONLY

### 1. ETA, Routing Distance, and Trajectories
- **Status**: `SIMULATED_ONLY`
- **Evidence**: `utils/pricing.ts` explicitly notes it is a "Mock implementation for MVP to calculate dynamic pricing and distance." 
- **Mechanism**: Instead of real-time mapping APIs, the engine uses a deterministic pseudo-random string hash (`simpleHash(pickup + dropoff)`) to calculate `distanceMiles` and `durationMinutes`.

### 2. Preparation Times and Surge Pricing
- **Status**: `SIMULATED_ONLY` / `SYNTHETIC_ONLY`
- **Evidence**: `merchant_reliability_scores` uses aggregated synthesized data for `avg_prep_time_mins`. Surge multipliers (`surgeMultiplier`) in the ride pricing engine are calculated via minute-of-day offsets and hash-based zone modifiers rather than actual `OBSERVED` supply/demand graphs.

### 3. Arrival Replays and ML Intelligence
- **Status**: `SIMULATED_ONLY`
- **Evidence**: 
  - ML predictive models (ZonePilot logic) are currently bypassed by injecting static `ml_score_logs` during the database seed process to mimic anomaly detection.
  - Live map tracking updates depend on state transitions rather than true live GPS telemetry streams.

### 4. ZonePilot Data Variable Readiness
- Order-arrival replay: `SIMULATED_ONLY`
- Preparation-time modeling: `SYNTHETIC_ONLY`
- Promised-vs-actual ETA: `SIMULATED_ONLY`
- Rider assignment timing: `DERIVABLE` (via standard DB `created_at` records on job acceptance)
- Rider acceptance: `OBSERVED` (boolean acceptance recorded in job row)
- Pickup timing: `DERIVABLE` (status updates logged, but lacks high-frequency GPS proof)
- Completion timing: `OBSERVED` (final status updated recorded)
- Cancellation/refund analysis: `SYNTHETIC_ONLY` (refund records exist primarily via seed data)
- Rider utilization: `MISSING` (no real session tracking)
- Batching: `MISSING` (C dispatch doesn't batch natively)
- Queue reconstruction: `MISSING`
- Unit-economics proxies: `DERIVABLE` (pricing algorithms exist, though simulated)
- H3/geospatial enrichment: `MISSING`
- Counterfactual simulation: `MISSING`

### Conclusion
The frontend and database schemas are structurally ready to consume ZonePilot data, but the current data feeds are strictly mocked and deterministic. To transition to an `OBSERVED` state for a laboratory experiment, the deterministic hashing and faker integrations must be swapped with live telemetry streams (or historical replay streams) and actual ML inference endpoints.

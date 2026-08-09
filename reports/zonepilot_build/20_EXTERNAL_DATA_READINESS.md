# 20_EXTERNAL_DATA_READINESS (V2)

## ACTUAL DATA ON DISK

### 1. Weather Context
- **Weather rows (Historical)**: 26,280 (365 days x 24 hours x 3 sampled points `hsr`, `krm`, `ind`) successfully fetched using spatial sampling.
- **Weather date range**: `2025-08-09` to `2026-08-08` (Rolling 365 days)
- **Forecast snapshots**: 1 forecast acquisition run containing 144 forecast rows (48 hours x 3 sampled zones).

### 2. Traffic Context
- **Traffic historical rows/segments/routes**: 0 (Waiting on TomTom Traffic Stats Subscription/Quota confirmation).
- **Traffic date range**: N/A
- **Live traffic snapshots**: 3 route observations. 

### 3. Geographical Context
- **OSM nodes**: Not fully extracted.
- **OSM edges**: Not fully extracted.
- **POIs**: Not fully extracted.
- **H3 cells**: Not fully extracted.
- **OSRM routes**: Matrix computation pending graph build.
- **ONDC rows**: 0 (Aggregates API requires live endpoint mapping).

### 4. Storage and Pipeline Integrity
- **Missing intervals**: 0 gaps in OpenMeteo weather between `2025-08-09` and `2026-08-08`.
- **Disk usage**: ~2.54 MB raw / GitHub Artifact sizing to be determined on remote.
- **Earliest timestamp**: `2025-08-09T00:00:00+05:30` (Weather)
- **Latest timestamp**: `2026-08-10T12:00:00+05:30` (Forecast snapshots)

## ML READINESS GATE
**Verdict:** `NOT_READY`

*Note on Flagship Experiment:*
The flagship experiment predicts externally observable physical-network degradation and travel-time degradation. **Swiggy/Zomato orders are NOT required for the core thesis.**
The minimum ML readiness gate requires:
1. Real historical traffic
2. Real weather
3. Real road graph
4. Reproducible temporal features
5. Adequate temporal/spatial coverage
6. Future-leakage protections

We are missing #1 and #3.

## SHADOW-OPERATION READINESS GATE
**Verdict:** `SHADOW_OPERATION_NOT_READY`

True readiness requires:
1. Capture state at T.
2. Build feature vector using only information available at T.
3. Make +15/+30/+60 prediction.
4. Freeze prediction.
5. Later retrieve real future traffic/network observations.
6. Match future outcome.
7. Score error/calibration.
8. Append immutable Decision/Forecast + Outcome records.

Currently, we only have the raw snapshot capability (Open-Meteo forecasts). The end-to-end outcome matching and error scoring loop is not yet built.

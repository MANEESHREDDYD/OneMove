# OneMove — Canonical Data Contract & Evidence Model

## Evidence Classes

Every data asset in OneMove is formally assigned an evidence class:

1. `OBSERVED`: Raw telemetry from physical sensors or authoritative API providers (e.g. Open-Meteo precipitation, TomTom live speed).
2. `PUBLIC_GEOGRAPHIC`: Verified geospatial boundaries and graph topologies (e.g. OpenStreetMap road networks, Uber H3 Resolution-8 hexagons).
3. `PUBLIC_OFFICIAL`: Official government census data, administrative boundaries, and demographic registries.
4. `DERIVED`: Deterministic algorithmic outputs calculated from observed/geographic sources (e.g. OSRM travel duration matrices, speed baseline medians).
5. `SIMULATED`: Synthetic counterfactual conditions for stress-testing and resilience simulation (e.g. Silk Board corridor closure, 35mm/hr torrential rain injection).
6. `ASSUMPTION`: Transparent economic unit costs and operational bounds (e.g. rider hourly wage rate, warehouse lease costs).

## Geospatial Spatial Partitioning Standard

- **Partitioning Method**: Uber H3 Discrete Global Grid System
- **Resolution**: Resolution 8 (average hexagon area $\approx 0.737 \text{ km}^2$, edge length $\approx 461 \text{ m}$)
- **Boundary**: Bengaluru Urban District (94 contiguous gold cells)
- **Cell IDs**: Verified authentic Hex strings (e.g. `886189255bfffff`)

## OSRM Travel Duration Matrix Standard

- **Dimensions**: 12 Candidate Facilities $\times$ 94 Demand Zones
- **Units**: Seconds
- **Storage Location**: `data_root/private/official/gold/r1_osrm_travel_matrix.json` & GCS `zonepilot-<env>-artifacts-9a4285`
- **Integrity**: Immutable SHA-256 hash verified at optimizer initialization

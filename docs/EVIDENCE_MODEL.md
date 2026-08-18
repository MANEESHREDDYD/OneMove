# ZonePilot Evidence Model & Data Taxonomy

## 1. Core Principle

In ZonePilot, **no metric, recommendation, or optimization result is presented without verifiable evidence lineage.**

Every data asset, baseline calculation, and scenario model is taxonomically classified into one of six standard evidence classes:

| Evidence Class | Definition | Example in ZonePilot |
|---|---|---|
| `OBSERVED` | Direct telemetry or physical sensor observation from an external provider. | Open-Meteo 9,024 hourly weather records, TomTom traffic speeds. |
| `PUBLIC_GEOGRAPHIC` | Verified open-source geographic spatial entities and road graphs. | OpenStreetMap Bengaluru road network, Uber H3 Resolution 8 cells. |
| `PUBLIC_OFFICIAL` | Official government registries, census figures, or spatial boundaries. | BBMP municipal boundaries, official pin code registries. |
| `DERIVED` | Deterministically computed mathematical outputs from verified inputs. | OSRM all-pairs travel matrix, spatial demand weights. |
| `SIMULATED` | Synthetic disruption scenarios injected under controlled stress parameters. | Outer Ring Road closure, depot transformer outage. |
| `ASSUMPTION` | Explicit operational proxy weights, penalty parameters, and cost bounds. | Objective function weights ($\text{expected}=5000, \text{p95}=1000$). |

## 2. Cryptographic Manifests & Hashing

Every dataset and map layer registered in the system generates an immutable SHA-256 content hash:
- `openmeteo-weather-forecast-h3`: Verified hourly telemetry across 94 cells.
- `pilot-network-zones`: Verified 94 H3 polygons with deterministic coordinate vertices.
- `osrm-canonical-matrix`: Verified travel durations computed by OSRM routing engine.

All run manifests are stored immutably with run IDs, timestamps, and schema version numbers.

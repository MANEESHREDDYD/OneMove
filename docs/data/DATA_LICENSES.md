# OneMove Data Licenses & Artifact Supply Chain Audit

This document records the authoritative license, redistribution, provenance, and sensitivity audit for all tracked data artifacts and supply chain fixtures in the OneMove repository.

---

## 1. Executive Summary & Repository Boundary

- **Public Repository Model**: OneMove contains source code, verifiable public/derived dataset schemas, cryptographic manifests, and test fixtures.
- **Strict Boundary**: No secret API keys, private passwords, PII (Personally Identifiable Information), or proprietary non-redistributable data are tracked.
- **Deterministic Replay Guarantee**: All spatial indexes, routing matrices, and test fixtures are derived from open public sources (OpenStreetMap, Open-Meteo) under permissive/open attribution licenses.

---

## 2. Tracked Data Artifacts Audit Table

| Artifact Path | Source | License | Publicly Redistributable? | Sensitive / PII? | Commercial Restrictions? | Description & Attribution |
|:---|:---|:---|:---:|:---:|:---:|:---|
| `data/private/official/gold/gold_network_h3_8.b64` | OpenStreetMap contributors / Derived H3 spatial index | Open Database License (ODbL) 1.0 / CC-BY-SA 2.0 | **YES** | **NO** | **NO** (with ODbL attribution) | Base64-encoded representation of the 94 H3 Resolution-8 hexagon feature table containing aggregated POI/road counts. |
| `data/private/official/gold/r1_osrm_travel_matrix.json` | OSRM computed from OpenStreetMap road network | ODbL 1.0 / BSD 2-Clause (OSRM) | **YES** | **NO** | **NO** (with ODbL attribution) | 12x94 deterministic travel duration matrix in seconds between candidate warehouse hubs and H3 demand zones. |
| `data/private/official/manifests/gold_manifest.json` | OneMove Build Pipeline | Apache-2.0 / MIT | **YES** | **NO** | **NO** | Cryptographic SHA-256 digests and row counts for Gold data verification. |
| `data/private/official/manifests/osrm_smoke_manifest.json` | OneMove Test Suite | Apache-2.0 / MIT | **YES** | **NO** | **NO** | Reference coordinates and test assertions for deterministic routing checks. |
| `data/private/official/manifests/OFFICIAL_DAILY_MANIFEST_2026-08-09.json` | OneMove Daily Snapshotter | Apache-2.0 / MIT | **YES** | **NO** | **NO** | Snapshot manifest metadata. |
| `data/private/official/raw/osrm/benchmark.json` | OSRM Benchmark Run | Apache-2.0 / MIT | **YES** | **NO** | **NO** | Timing statistics and latency measurements. |
| `data/bronze/bronze_data.json` | Synthetic Generator | Apache-2.0 / MIT | **YES** | **NO** | **NO** | Synthetic raw transaction schema fixtures. |
| `data/silver/silver_data.json` | Synthetic Generator | Apache-2.0 / MIT | **YES** | **NO** | **NO** | Synthetic validated schema fixtures. |
| `data/demo_exports/*.csv` | Synthetic Demo Seed | Apache-2.0 / MIT | **YES** | **NO** | **NO** | Anonymized synthetic commerce demo fixtures (orders, merchants, customers). |
| `data/dq/dq_report.json` | Great Expectations / Custom Validator | Apache-2.0 / MIT | **YES** | **NO** | **NO** | Data quality summary report. |

---

## 3. Upstream Attribution & License Terms

### OpenStreetMap (OSM)
- **License**: Open Database License (ODbL) 1.0 (https://opendatacommons.org/licenses/odbl/)
- **Attribution**: "© OpenStreetMap contributors"
- **Redistribution**: Derived spatial networks and aggregated geometric indexes may be shared under ODbL with proper contributor attribution.

### Open-Meteo Weather Data
- **License**: Creative Commons Attribution 4.0 International (CC-BY 4.0) (https://open-meteo.com/en/terms)
- **Attribution**: "Weather data by Open-Meteo.com"
- **Usage**: Used for precipitation and temperature resilience scenario calibration.

### Project OSRM (Open Source Routing Machine)
- **License**: BSD 2-Clause License
- **Usage**: Deterministic matrix generation for multimodal commerce optimization.

---

## 4. Compliance Verification

1. **Zero Secret Leakage**: Continuous automated scans via CodeQL, Ruff, and Trufflehog verify that no AWS/GCP credentials, database passwords, or JWT signing secrets exist in the repository tree.
2. **Deterministic Reconstitution**: CI workflows bootstrap `gold_network_h3_8.parquet` via `scripts/bootstrap_ci_artifacts.py` and verify SHA-256 `7d8973d37a73d86000b066a2e955ea7421d3fa4a878d3538a8114b6a5221747e` before executing tests.

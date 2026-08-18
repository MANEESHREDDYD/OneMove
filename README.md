# ZonePilot — Spatial Decision Intelligence Platform

[![CI/CD Status](https://github.com/MANEESHREDDYD/OneMove/actions/workflows/python.yml/badge.svg)](https://github.com/MANEESHREDDYD/OneMove/actions)
[![Next.js 16.3 Turbopack](https://img.shields.io/badge/Next.js-16.3%20Turbopack-black)](https://nextjs.org/)
[![Python 3.11/3.12](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue)](https://python.org/)
[![PostgreSQL 15](https://img.shields.io/badge/PostgreSQL-15%20(Supabase)-336791)](https://supabase.com/)
[![OR-Tools CP-SAT](https://img.shields.io/badge/Google%20OR--Tools-CP--SAT%20Solver-orange)](https://developers.google.com/optimization)

**ZonePilot** is an enterprise-grade spatial decision intelligence and network optimization platform engineered for urban logistics, facility placement, multi-scenario resilience evaluation, and Point-In-Time auditable decision tracking.

ZonePilot is built on an authentic **94-cell Uber H3 (Resolution 8)** spatial partitioning of Bengaluru Urban, with real OpenStreetMap road networks, real-world Open-Meteo weather telemetry, deterministic CP-SAT optimization, and zero mock fallbacks.

---

## System Architecture

```mermaid
graph TD
    A[Observatory Frontend<br/>Next.js 16.3 App Router] -->|JWT + Tenancy Headers| B[FastAPI Gateway<br/>services/api]
    B --> C[PostgreSQL Database<br/>Supabase Pooler + RLS]
    B --> D[Optimization Engine<br/>Google OR-Tools CP-SAT]
    B --> E[Resilience Engine<br/>Network Breaker]
    B --> F[Decision Ledger<br/>Point-In-Time Replay]
    B --> G[Forecast Engine<br/>Causal Baselines]
    H[Private Data Plane<br/>ZonePilot-Data] -->|Ingestion & Lineage| C
```

---

## Key Capabilities

### 1. Deterministic Multi-Scenario Facility Optimization (R3)
- **Mathematical Engine:** Google OR-Tools CP-SAT constraint satisfaction solver.
- **Problem Scale:** 94 demand cells $\times$ 12 candidate facilities $\times$ 3 uncertainty scenarios (Free Flow, Congested, Compound Outage).
- **Exact Lineage:** Deterministic lexicographical tie-breaking guaranteeing identical decisions given identical inputs.
- **Persistence:** All optimization jobs, solver states, wall-clock latencies, and Pareto frontiers are durably persisted in `public.optimization_jobs` and `public.optimization_results`.

### 2. Resilience Engine & Network Breaker (R4)
- **Stress-Testing Suite:** Evaluates network degradation under primary corridor cuts (e.g. Silk Board / Outer Ring Road), depot transformer failures, and severe monsoon precipitation (35mm/hr).
- **Quantile Computation:** P50, P90, and P95 tail latency percentiles, disconnected zone counts, and failure exposure scores.
- **Automated Grading:** Deterministic failure classification (`ROBUST`, `MODERATE_DEGRADATION`, `SEVERE_DEGRADATION`, `CRITICAL_FAILURE`).

### 3. Point-In-Time Causality & Decision Time Travel (R7)
- **Anti-Leakage Guarantee:** Decision replay strictly enforces $\text{Information Available At} \le \text{Decision Time}$.
- **Immutable Ledger:** Every operational decision records its exact code SHA, dataset version, and input snapshot hash.
- **Prospective Shadow Validation:** Freezes decisions into future observation windows to bound regret against actual observed conditions.

### 4. Evidence Model & Artifact Taxonomy (A1)
- **Formal Taxonomy:** Every piece of data is tagged with its evidence class:
  - `OBSERVED`: Real sensor or provider observations (Open-Meteo, TomTom).
  - `PUBLIC_GEOGRAPHIC`: OpenStreetMap road networks and Uber H3 hexagons.
  - `PUBLIC_OFFICIAL`: Official government census and spatial registries.
  - `DERIVED`: Deterministic OSRM travel matrices and speed baselines.
  - `SIMULATED`: Synthetic disruption injections.
  - `ASSUMPTION`: Explicit proxy economics and cost models.
- **Cryptographic Lineage:** Every dataset and map layer exposes an immutable SHA-256 manifest hash.

### 5. Typed Operational Assistant (R8)
- **Schema-Grounded AI:** Grounded strictly in verified evidence records from PostgreSQL.
- **Constraint Explanations:** Explains why facilities were opened and provides direct evidence lineage IDs while refusing ungrounded queries.

---

## Observatory Product Suite (12 Routes)

The Next.js Observatory frontend (`apps/observatory`) delivers 12 comprehensive operational routes:

| Route | View Name | Purpose |
|---|---|---|
| `/` | **Operations Dashboard** | System overview, real-time metrics, provider freshness, and fast navigation. |
| `/network` | **94-Cell Network Topology** | Interactive Leaflet map with 94 H3 Res 8 cells, GIS layer overlays, and zone inspector. |
| `/data-health` | **Data Health & SLA** | Provider freshness tracking, SLA compliance, DQ test results, and dataset catalog. |
| `/system-health` | **Infrastructure Health** | Real-time Railway API status, database pooler latency, and backend version check. |
| `/optimize` | **Facility Optimizer** | Interactive CP-SAT constraint configuration, solver launcher, and Pareto frontier. |
| `/resilience` | **Network Breaker** | Failure injection bench, road closures, and P50/P90/P95 tail latency inspector. |
| `/scenarios` | **Scenario Lab** | Simulation matrix running compound environmental stress tests against baseline. |
| `/experiments` | **Experiment Registry** | Validated benchmark suite for EXP-01 (CP-SAT), EXP-02 (Resilience), EXP-03 (PIT), EXP-04 (Shadows). |
| `/decisions` | **Decision Ledger** | Immutable audit trail of recorded optimizations and opened facility sets. |
| `/replay` | **Time Travel Replay** | Authentic Point-In-Time causality verifier with mathematical reproduction proof. |
| `/evidence` | **Evidence Inspector** | Complete taxonomic evidence register with SHA-256 cryptographic hashes. |
| `/assistant` | **Typed Assistant** | Evidence-grounded operator assistant with formal schema grounding. |

---

## Verification & Test Results

```bash
# Python Backend Test Suite (100% Passing)
pytest tests/
# Result: 211 passed, 55 skipped in 90.27s

# Frontend Vitest Suite (100% Passing)
npm --prefix apps/observatory run test
# Result: 87 passed (8 test files)

# TypeScript Typecheck
npm --prefix apps/observatory run typecheck
# Result: 0 errors

# Production Next.js Turbopack Build
npm --prefix apps/observatory run build
# Result: 17 static & dynamic routes compiled successfully
```

---

## Local Development Quickstart

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ (or Supabase project)

### 1. Backend Setup
```bash
# Install dependencies
pip install -e .

# Set database environment variable
export DATABASE_URL="postgresql://postgres:password@localhost:5432/postgres"

# Start FastAPI server
uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
# Install dependencies
cd apps/observatory
npm install

# Start Next.js development server
npm run dev
```

Visit `http://localhost:3000` to access the ZonePilot Observatory.

---

## License
Apache-2.0

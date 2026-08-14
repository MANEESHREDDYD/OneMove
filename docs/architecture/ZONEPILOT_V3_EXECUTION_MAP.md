# ZONEPILOT V3 EXECUTION MAP

## Agent 0: Principal Integrator
- **Owned Paths**: `docs/architecture/`, CI pipelines, release gates.
- **Milestone**: R0.5 through R9 orchestration.
- **Merge Status**: ACTIVE.

## Wave 1 (Real World + Temporal Network Foundation)
### Agent B: Real Data Platform / ETL
- **Owned Paths**: `services/collectors/`, `services/zonepilot/etl/`
- **Dependencies**: R0.5 GitHub Actions Automation
- **Milestone**: R1
- **Merge Status**: PENDING R0.5 GO

### Agent C: Geospatial / OSRM / H3 / Temporal Graph
- **Owned Paths**: `services/zonepilot/geospatial/`, `services/zonepilot/routing/`
- **Dependencies**: Agent B (Raw/Bronze Data)
- **Milestone**: R1
- **Merge Status**: PENDING

### Agent G: Database / Backend Core / Auth Foundation
- **Owned Paths**: `services/zonepilot/backend/`, Supabase migrations
- **Dependencies**: R0.5 Supabase setup
- **Milestone**: R1
- **Merge Status**: PENDING

## Wave 2 (Temporal Network + Product/API)
### Agent D: Temporal Network + Forecasting / ML
- **Owned Paths**: `services/zonepilot/features/`, `services/zonepilot/forecasting/`
- **Dependencies**: Wave 1 (R1 GO)
- **Milestone**: R2

### Agent H: Frontend / Visualization / Product UX
- **Owned Paths**: Next.js frontend (`/network`, `/replay`, etc.)
- **Dependencies**: Wave 1 (R1 GO), Agent I (APIs)
- **Milestone**: R2

### Agent I: API Contracts / Job Execution
- **Owned Paths**: FastAPI public contracts (`/api/v1`)
- **Dependencies**: Wave 1 (R1 GO)
- **Milestone**: R2

## Wave 3 (Optimization + Resilience + Economics)
### Agent E: Robust Facility / Capacity Optimization
- **Owned Paths**: `services/zonepilot/optimization/`
- **Dependencies**: Wave 2 (R2 GO)
- **Milestone**: R3

### Agent F: Resilience / Simulation / Recovery
- **Owned Paths**: `services/zonepilot/simulation/`, `services/zonepilot/resilience/`
- **Dependencies**: Wave 2 (R2 GO)
- **Milestone**: R4

### Agent J: Economics + Experimentation
- **Owned Paths**: `services/zonepilot/economics/`, `experiments/`
- **Dependencies**: Wave 2 (R2 GO)
- **Milestone**: R5

## Wave 4 (Shadow Operations + Production Hardening)
### Agent K: Decision Ledger / Shadow Operations
- **Owned Paths**: `services/zonepilot/decision/`
- **Dependencies**: Wave 3
- **Milestone**: R7

### Agent L: Security / Reliability / Observability / Performance
- **Owned Paths**: Threat models, Sentry, rate limits
- **Dependencies**: Wave 3
- **Milestone**: R6

## Wave 5 (LLM / Swiggy Product Integration)
### Agent M: Evidence-Grounded Assistant + Swiggy MCP
- **Owned Paths**: `services/zonepilot/assistant/`, `services/collectors/platforms/swiggy/`
- **Dependencies**: Wave 4 (R6/R7 GO)
- **Milestone**: R8/R9

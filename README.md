# OneMove

OneMove is an evidence-backed decision intelligence platform for physical-commerce networks. It combines geographic network state, scenario simulation, optimization and point-in-time decision provenance so operators can compare doing nothing with recommended actions and reproduce why a decision was made.

Built by Maneesh Reddy Duddukunta

---

## Problem

Operators make network decisions across fragmented geographic, traffic, weather, demand and operational systems. The decision is expensive, slow to reverse, and made against a network that changes: roads congest, monsoon rain inflates travel times, a corridor closes. When the decision is later challenged, the organization cannot reconstruct what was known at the time it was made.

## What OneMove Does

OneMove takes a city network, a set of candidate facility locations, and an explicitly declared set of assumptions, and produces a facility-placement decision that can be re-derived later from the same inputs.

### Operate / Simulate / Decide / Prove

- **Operate**: Read the current network state with live traffic and weather context. Every number carries an evidence class.
- **Simulate**: Apply a counterfactual to the authentic baseline — a travel-time inflation, a corridor cut, a heavy-rain scenario.
- **Decide**: Compare doing nothing with recommended action. Submit an optimization and evaluate the tradeoffs.
- **Prove**: Record why the decision was made, freeze the evidence, and replay it later point-in-time.

## Demo

The interactive demo executes a 16-order simulated delivery mission over real Bengaluru geography. It walks through network operation, disruption simulation, CP-SAT optimization, and the final decision freeze.

### What Is Real in the Demo?

- **Geography** — `PUBLIC_GEOGRAPHIC` (OpenStreetMap / H3)
- **Traffic** — `PROVIDER_ESTIMATED` (TomTom)
- **Weather** — `PUBLIC_OFFICIAL` (Open-Meteo)
- **Orders** — `SIMULATED`
- **Scenario** — `SIMULATED`
- **Recommendation** — `DERIVED` (OR-Tools CP-SAT)
- **Business economics** — `NOT MODELED`

*Note: The demo does not use data from Swiggy, Zomato, Zepto, or any other private enterprise. All delivery missions are explicitly simulated.*

## Architecture

```
OpenStreetMap / H3
        │
        ├───────────────┐
        │               │
TomTom Traffic     Open-Meteo
        │               │
        └───────┬───────┘
                │
        Evidence / Data Layer
                │
        Scenario Construction
                │
       OR-Tools CP-SAT
                │
    Baseline vs Recommendation
                │
         Deterministic WHY
                │
     PostgreSQL Decision Ledger
                │
          PIT Replay
                │
             FastAPI
                │
             Next.js
                │
            MapLibre
```

## Optimization

Google OR-Tools CP-SAT powers the engine. The model chooses which candidate facilities to open and assigns every demand zone, minimizing a weighted objective with expected travel, P95 travel, facility cost, failure exposure, and coverage loss.

### Do Nothing vs Recommended

Instead of showing only an optimizer result, OneMove compares the recommendation with doing nothing under the same problem, assumptions, travel matrices, and policy. It surfaces changes in coverage and expected travel explicitly.

### Decision Explanation

The explanation is deterministic. It exposes which objective components improved, which tradeoff worsened, the assumptions used, and the evidence behind the decision. There is no LLM-generated hallucination in the decision rationale.

### Evidence / PIT Replay

A frozen decision record carries the authoritative solver result, the input snapshot hash, the assumption-set digest, the release identity, and a per-node evidence chain.
The decision can then be replayed from its frozen evidence to prove it exactly reproduces the action, or to quantify exactly how it diverges.

## Testing

The backend is verified by a pytest suite covering deterministic optimization, decision freezing, and point-in-time temporal isolation. The frontend uses Vitest and Playwright. The database leverages PostgreSQL.

## Known Limitations

- Bengaluru pilot only.
- Delivery mission is simulated.
- Routing is road-network based but not traffic-aware.
- Current provider freshness depends on external availability.
- Business economics are not modeled.
- Historical backtesting is not yet part of the outreach demo.
- Human approval/override lifecycle is not yet the final production workflow.
- Multi-city and large-scale operational performance are not yet certified.
- Outreach demo readiness does not equal production readiness.

## Demo Runbook

See `docs/CTO_DEMO_RUNBOOK.md` for instructions to execute the golden path demo.

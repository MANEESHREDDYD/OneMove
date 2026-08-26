# OneMove

**Physical-commerce network decision intelligence.**

Author: Maneesh Reddy Duddukunta

## Problem

Operators make network decisions across fragmented geographic, traffic, weather, demand and operational systems.

## What OneMove Does
- **OPERATE**: See what is happening.
- **SIMULATE**: Model what could happen.
- **DECIDE**: Compare doing nothing with recommended action.
- **PROVE**: Record why the decision was made and replay it later.

## Demo Proof
- Real Bengaluru road geography
- Current provider context
- 16 simulated delivery orders
- Simulated disruption
- CP-SAT optimization
- Do Nothing baseline
- Recommended action
- Deterministic WHY
- Frozen evidence
- PIT replay

## What Is Real?
- **Geography** — PUBLIC_GEOGRAPHIC
- **Traffic** — PROVIDER_ESTIMATED
- **Weather** — PUBLIC_OFFICIAL
- **Orders** — SIMULATED
- **Scenario** — SIMULATED
- **Recommendation** — DERIVED
- **Business economics** — NOT MODELED

## Architecture
```mermaid
graph TD
    classDef publicGeo fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#e2e8f0
    classDef provEst fill:#1e293b,stroke:#f59e0b,stroke-width:2px,color:#e2e8f0
    classDef pubOff fill:#1e293b,stroke:#34d399,stroke-width:2px,color:#e2e8f0
    classDef sim fill:#1e293b,stroke:#ec4899,stroke-width:2px,color:#e2e8f0
    classDef derived fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#e2e8f0

    A["OpenStreetMap / H3<br/><small><i>PUBLIC_GEOGRAPHIC</i></small>"]:::publicGeo
    B["TomTom Traffic<br/><small><i>PROVIDER_ESTIMATED</i></small>"]:::provEst
    C["Open-Meteo<br/><small><i>PUBLIC_OFFICIAL</i></small>"]:::pubOff

    A --> E[Evidence Layer]
    B --> E
    C --> E

    E --> F["Scenario Construction<br/><small><i>SIMULATED / ASSUMPTION</i></small>"]:::sim
    F --> R["Road / Graph Routing<br/><small><i>DERIVED</i></small>"]:::derived
    R --> G["OR-Tools CP-SAT<br/><small><i>DERIVED</i></small>"]:::derived
    G --> H["Baseline vs Recommendation<br/><small><i>DERIVED</i></small>"]:::derived
    H --> I[Deterministic WHY]
    I --> J[(PostgreSQL Decision Ledger)]
    J --> K[PIT Replay]
```

## Current Limitations
- Single Bengaluru pilot
- 16-order outreach mission
- Routing is road-network based but not traffic-aware
- Current provider freshness depends on external availability
- No real retailer/customer data
- Business economics are not modeled
- Continuous production scheduling not yet certified
- Human approval/override workflow not yet final production workflow
- Multi-city scale not yet demonstrated

## Contact
Maneesh Reddy Duddukunta
[GitHub](https://github.com/MANEESHREDDYD)

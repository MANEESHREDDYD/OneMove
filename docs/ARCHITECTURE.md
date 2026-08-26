# OneMove Architecture

OneMove is designed to capture changing network conditions and produce explainable, reproducible decisions.

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

    A --> E[Evidence / Data Layer]
    B --> E
    C --> E

    Mission["Mission Data<br/><small><i>SIMULATED</i></small>"]:::sim --> F

    E --> F["Scenario Construction<br/><small><i>SIMULATED / ASSUMPTION</i></small>"]:::sim

    F --> R["Road / Graph Routing<br/><small><i>DERIVED</i></small>"]:::derived
    R --> G["OR-Tools CP-SAT<br/><small><i>DERIVED</i></small>"]:::derived

    G --> H["Baseline vs Recommendation<br/><small><i>DERIVED</i></small>"]:::derived

    H --> I[Deterministic WHY]

    I --> J[(PostgreSQL Decision Ledger)]

    J --> K[PIT Replay]

    K --> L[FastAPI]
    L --> M[Next.js]
    M --> N[MapLibre]
```

## Evidence Provenance

- **OpenStreetMap / H3**: Base geographic topology and canonical regional divisions (PUBLIC_GEOGRAPHIC)
- **TomTom**: Current traffic speeds and congestion estimates (PROVIDER_ESTIMATED)
- **Open-Meteo**: Weather context (PUBLIC_OFFICIAL)
- **Mission & Scenario**: 16-order delivery data and a controlled facility disruption (SIMULATED)
- **Business inputs**: Declared optimization inputs (ASSUMPTION); capacity is not modeled in this demo
- **Optimization & Recommendation**: The CP-SAT output and expected objective comparisons (DERIVED)

## Core Stack

- **Frontend**: Next.js (React), MapLibre GL JS
- **API**: FastAPI (Python)
- **Solver**: OR-Tools CP-SAT
- **Storage**: PostgreSQL (psycopg 3)

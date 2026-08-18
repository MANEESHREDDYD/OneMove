# OneMove — Architecture Dependency Graph

```mermaid
graph TD
    classDef realData fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#fff;
    classDef compute fill:#14532d,stroke:#22c55e,stroke-width:2px,color:#fff;
    classDef platform fill:#701a75,stroke:#d946ef,stroke-width:2px,color:#fff;
    classDef governance fill:#7c2d12,stroke:#f97316,stroke-width:2px,color:#fff;
    classDef adversarial fill:#881337,stroke:#f43f5e,stroke-width:2px,color:#fff;

    %% Data Plane
    A0[A0: Real Data ETL<br/>Open-Meteo & Weather]:::realData --> A2[A2: Temporal & Forecast<br/>Causal Baselines]:::compute
    A0 --> H5[H5: Data Governance<br/>Lineage & Integrity]:::governance
    
    %% Geospatial & Network
    A1[A1: GIS / H3 / OSRM<br/>94 H3 Cells & Travel Matrix]:::realData --> A2
    A1 --> A3[A3: Optimization<br/>Google OR-Tools CP-SAT]:::compute
    A1 --> A4[A4: Resilience Engine<br/>Stress Testing]:::compute
    A1 --> A7[A7: Decision Ledger<br/>Point-In-Time Replay]:::compute
    A1 --> A9[A9: OneMove Frontend<br/>Observatory UI]:::platform

    %% Compute & Optimization
    A2 --> A3
    A2 --> A7
    A2 --> A8[A8: AI Assistant<br/>Grounded Explanation]:::compute
    A2 --> A9
    A2 --> H5
    
    A3 --> A4
    A3 --> A5[A5: Economics<br/>Assumption Registry]:::compute
    A3 --> A7
    A3 --> A8
    A3 --> A9

    A4 --> A5
    A4 --> A7
    A4 --> A8
    A4 --> A9

    A5 --> A7
    A5 --> A9

    %% Platform & Infrastructure
    A6[A6: GCP Platform & SRE<br/>Cloud Run & PubSub]:::platform --> ALL_STREAMS[All Subsystems]
    
    %% Outcomes & Ledger
    A7 --> A8
    A7 --> A9
    A7 --> H5
    A8 --> A9

    %% Governance & Integration
    H1[H1: Principal Architect<br/>Contracts & C4]:::governance --> ALL_STREAMS
    H2[H2: End-to-End Journey<br/>Operator Workflow]:::governance --> A9
    H3[H3: Independent QA<br/>Release Auditing]:::governance --> ALL_STREAMS
    H4[H4: Security & IAM<br/>Fail-Closed Auth & RLS]:::governance --> ALL_STREAMS

    %% Adversarial Red Team
    X1[X1: Adversarial Red Team<br/>Hostile Attack Lab]:::adversarial --> ALL_STREAMS
    X1 --> X2[X2: Hard Remediation<br/>Root-Cause & Regression]:::adversarial
    X2 --> H3
```

## Stream Interfaces & Contract Boundary

1. **A0 $\to$ Data Lake / PostgreSQL**: Raw immutable weather telemetry and sensor observation payloads.
2. **A1 $\to$ A3 / A4**: Authentic 12x94 OSRM precomputed matrix with SHA-256 integrity verification.
3. **A3 $\to$ Pub/Sub $\to$ A6 Worker**: Asynchronous optimization job requests and durable result persistence.
4. **A7 $\to$ Database**: Strict append-only decision records with full Point-in-Time input snapshots.
5. **H4 $\to$ API Gateway**: Fail-closed bearer token verification requiring workspace and user claims.
6. **X1 $\to$ Failure Ledger $\to$ X2**: Zero-tolerance defect lifecycle requiring unit regression tests and postmortems.

import os

docs = {
    "docs/system/ARCHITECTURE.md": """# ZonePilot Architecture

## Operational Cloud Plane
The operational plane handles live data collection and volunteer interactions. It consists of the Observatory PWA (Next.js 16) hosted on Vercel, which communicates with a FastAPI backend hosted on Railway. Authentication uses Supabase invite-only Auth, and data lands in the Supabase Postgres `zonepilot` schema. Railway also runs cron collectors.

## Private Research Plane
This is an offline/local environment on the owner's laptop. It uses `zonepilot snapshot-pull` to download operational state into `$ZONEPILOT_DATA_ROOT/private/raw`, processes it through bronze/silver/gold Parquet layers, queries via DuckDB, and evaluates counterfactual policies via CP-SAT and digital twin simulations.

## Isolation
The Swiggy MCP Companion remains entirely physically and logically separate from the ZonePilot research modules.
""",
    "docs/system/DATA_FLOW.md": """# Data Flow

```mermaid
graph TD
    subgraph Operational Cloud Plane
        PWA[Observatory PWA] --> API[FastAPI]
        API --> DB[Supabase Postgres]
        Cron[Railway Cron] --> DB
    end
    subgraph Merchant Path
        Merchant[Merchant File] --> Temp[Encrypted Temp Area]
        Temp --> Importer[Local CLI Importer]
        Importer --> DB
    end
    subgraph Private Research Plane
        DB --> Pull[Snapshot Pull]
        Pull --> Raw[Raw Parquet]
        Raw --> Bronze --> Silver --> Gold
        Gold --> DuckDB
        DuckDB --> Models[Training/Simulation]
    end
    Models --> Export[make public-export]
```
""",
    "docs/system/TRUST_BOUNDARIES.md": """# Trust Boundaries

```mermaid
graph TD
    subgraph Untrusted / Client
        Observer[Observer Device]
        Volunteer[Volunteer Device]
    end
    subgraph Trusted Operational Cloud
        API[FastAPI / RLS Enforced]
        DB[Supabase]
    end
    subgraph Strictly Private Owner Environment
        Research[Local Data Root / Models]
    end
    Observer -->|JWT / RLS| API
    Volunteer -->|JWT / RLS| API
    DB -->|Secret Key / Pull| Research
```
""",
    "docs/system/DEPLOYMENT_TOPOLOGY.md": """# Deployment Topology
- **Observatory PWA**: Vercel
- **FastAPI / ETL**: Railway
- **Database / Auth**: Supabase
- **Research Plane**: Local Machine (DuckDB / Python)
""",
    "docs/security/THREAT_MODEL.md": """# Threat Model
- **T1**: Contamination of study data by unauthenticated actors. (Mitigation: Invite-only auth, strict RLS).
- **T2**: Cross-tenant data leakage. (Mitigation: RLS scoping by study_id and participant_id).
- **T3**: PII leakage in public export. (Mitigation: Strict schema allowlisting on export, HMAC identifiers).
""",
    "docs/security/AUTHORIZATION_MODEL.md": """# Authorization Model
- **Human Sessions**: Always use RLS (`get_user_db(jwt)`).
- **Machine Jobs**: Use secret client (`get_service_db()`) strictly for cron jobs, collectors, and exports.
- **Roles**: CUSTOMER, MERCHANT, RIDER, SYSTEM, UNKNOWN. Managed safely.
""",
    "docs/data/PROVENANCE_MODEL.md": """# Provenance Model
All records must be stamped with a provenance enum:
- OBSERVED
- DERIVED
- ESTIMATED
- SIMULATED
- PUBLIC_BENCHMARK
- MERCHANT_CONFIDENTIAL
- DEMO_SYNTHETIC
- ASSUMPTION

Synthetic/Legacy OneMove data must be strictly quarantined.
""",
    "docs/data/SCHEMA_EVOLUTION.md": """# Schema Evolution
Migrations are immutable and ordered. No editing applied migrations.
Use `make schema-drift` to verify local schema matches canonical remote.
""",
    "docs/runbooks/STUDY_OPERATIONS.md": """# Study Operations
Runbook for starting, monitoring, and concluding a study zone execution.
""",
    "docs/runbooks/INCIDENT_RESPONSE.md": """# Incident Response
Runbook for data contamination or pipeline failures.
""",
    "docs/runbooks/OWNER_DAILY_RUNBOOK.md": """# Daily Runbook
Owner's daily tasks: check `/readyz`, run QC, review anomaly queue.
""",
}

adrs = {
    "ADR-001": (
        "Why single-node research architecture now; what changes at 100x",
        "Single node DuckDB is fast enough for the experiment scale. At 100x, requires distributed lakehouse.",
    ),
    "ADR-002": (
        "Railway cron instead of APScheduler/Airflow",
        "Railway is zero-ops and sufficient for basic collection tasks.",
    ),
    "ADR-003": (
        "DuckDB + Parquet instead of a warehouse/lakehouse",
        "Simplifies the private research plane and ensures reproducibility on a single laptop.",
    ),
    "ADR-004": ("Why no feature store", "Not running online inference, so offline generation is sufficient."),
    "ADR-005": (
        "Immutable snapshot manifests instead of DVC/LakeFS",
        "Simpler to manage explicitly versions snapshots for a static experiment window.",
    ),
    "ADR-006": (
        "Cloud operational plane vs private research plane",
        "Protects PII and raw data locally while keeping operations highly available.",
    ),
    "ADR-007": (
        "Append-only observational event model",
        "Ensures data is never silently mutated, preserving scientific validity.",
    ),
    "ADR-008": (
        "Why no LLM/fine-tuning in decision path",
        "Unnecessary latency, cost, and non-determinism for an operations research study.",
    ),
}

for path, content in docs.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

for num, (title, content) in adrs.items():
    path = f"docs/system/{num}_{title.replace(' ', '_').replace('/', '_')}.md"
    with open(path, "w") as f:
        f.write(f"# {num} - {title}\n\n## Decision\n{content}\n")

print("Generated architecture docs and ADRs.")

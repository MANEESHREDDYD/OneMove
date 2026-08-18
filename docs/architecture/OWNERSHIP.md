# OneMove — 17-Agent Engineering Stream Ownership

The canonical product name is **OneMove**. The internal engine and package namespace is retained as `zonepilot` to preserve stability and avoid unnecessary migration risk.

## Ownership Matrix

| Stream ID | Stream Name | Owner Description | Primary Directories Owned | Upstream Dependencies | Key Acceptance Gate |
|---|---|---|---|---|---|
| **A0** | Real Data Execution / ETL | Authentic Open-Meteo & spatial data acquisition plane | `services/zonepilot-data/`, `data_root/` | None | Real immutable payloads, strict schemas, quarantine on error |
| **A1** | GIS / H3 / OSM / OSRM | Authentic spatial network & routing matrices | `services/zonepilot/network/`, `data_root/official/gold/` | A0 | Authentic 12x94 OSRM matrix, immutable PBF/matrix digests |
| **A2** | Temporal / Forecasting / ML | Causal forecasting & observable network degradation | `services/zonepilot/forecast/`, `services/zonepilot/models/` | A0, A1 | Causal holdout evaluation, chronological ordering, no future leakage |
| **A3** | Optimization / Decision Science | Full 94x12x3 CP-SAT facility & capacity optimizer | `services/zonepilot/optimization/` | A1, A2 | Full 94x12x3 problem scale, deterministic tie-breaking, async execution |
| **A4** | Resilience / Counterfactuals | Stress-testing & multi-scenario network breaking | `services/zonepilot/resilience/` | A1, A3 | Simulated disruption grading (P50/P90/P95), side-effect free GET |
| **A5** | Economics / Experiments | Assumption registry & cost-benefit evaluation | `services/zonepilot/economics/`, `services/zonepilot/experiments/` | A3, A4 | Transparent assumptions, Pareto frontier, zero hidden magic constants |
| **A6** | GCP / Platform / SRE | Production cloud infrastructure, IaC & deployment | `infra/gcp/`, `.github/workflows/` | ALL | Terraform remote state, Cloud Run deployments, zero leak to non-OneMove |
| **A7** | Decision Ledger / Replay | Immutable decision tracking & PIT time travel | `services/zonepilot/decisions/` | A1, A2, A3, A4 | True PIT historical snapshot query, database write durability |
| **A8** | LLM / Assistant / AI Safety | Schema-grounded operational assistant & safety | `services/zonepilot/assistant/` | A7 | Typed tool execution, prompt injection defense, zero hallucinations |
| **A9** | Frontend / UX / Visualization | OneMove UI, map visualizer & operational console | `app/`, `components/`, `lib/` | ALL | Real API telemetry, WCAG AA accessibility, zero fake numbers |
| **H1** | Principal Architecture / Contracts | System architecture, contracts & C4 diagrams | `docs/architecture/`, `docs/contracts/` | ALL | OpenAPI adherence, C4 completeness, ADR documentation |
| **H2** | Product Journey / E2E Integration | Complete operator workflow integration | `tests/e2e/`, `tests/api/` | ALL | Unbroken real-data workflow from login to replay |
| **H3** | Independent QA / Verification | Release gate auditing, load & soak verification | `tests/`, `docs/release/` | ALL | 100% test pass, load testing, actual breaking point documented |
| **H4** | Security / IAM / Threat Modeling | Threat modeling, fail-closed auth & RBAC/RLS | `services/api/core/`, `docs/security/` | ALL | Strict fail-closed auth (401/403), zero P0/P1 security defects |
| **H5** | Data Quality / Governance | Data lineage, schemas & quality assurance | `docs/data/`, `services/zonepilot/governance/` | A0, A1, A2 | 100% manifest verification, cryptographic hashes, zero drift |
| **X1** | Adversarial Destroyer / Red Team | Hostile real-world fault injection & exploit lab | `docs/failure-lab/`, `tests/adversarial/` | ALL | Active search for crash, corruption, leakage, or calculation flaws |
| **X2** | Hard Remediation Engineer | Root-cause analysis, regression prevention | `docs/failure-lab/`, `docs/postmortems/` | X1 | Closed P0/P1 failures with deterministic regression tests |

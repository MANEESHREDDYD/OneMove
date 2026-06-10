# OneMove Competitive Readiness Gap Analysis

Audit date: 2026-06-10

Final conclusion:

- Portfolio competitive: YES
- Real production competitor: NO
- Production-preview/demo ready: only if all checks pass

OneMove is a strong private localhost portfolio demo for a full-stack Data/ML/AI marketplace intelligence platform. It should not be described as equal to DoorDash, Uber, Rapido, Swiggy, or Zomato at real-world production scale.

Public references reviewed:

- DoorDash developer and Drive API documentation: https://developer.doordash.com/en-US/
- Uber driver document requirements and safety/privacy material: https://www.uber.com/us/en/drive/requirements/documents/
- Rapido Captain terms and app listing: https://www.rapido.bike/CaptainTerms
- Swiggy partner onboarding support and delivery partner app listing: https://www.swiggy.com/support/issues/partner-onboarding
- Zomato terms, partner onboarding, and partner app listings: https://www.zomato.com/policies/terms-of-service/

| Area | What OneMove currently has | What real production companies have | Gap | Portfolio-ready status | Production blocker status |
|---|---|---|---|---|---|
| Real payments | Demo checkout records and scoped `payments` rows with demo statuses. | Processor integrations, payment intents, webhooks, settlement, tax invoices, dispute handling, refund rails, reconciliation, fraud checks. | No live processor, no money movement, no webhooks, no reconciliation. | YES | BLOCKER |
| Driver/partner onboarding | Demo partner account and partner dashboards/jobs. | Identity verification, document collection, vehicle checks, background checks, training, activation/deactivation, payout setup. | No KYC, no document workflow, no real eligibility workflow. | YES | BLOCKER |
| Merchant onboarding | Demo merchant account, catalog, order queue, merchant insights. | Legal onboarding, tax docs, bank details, menu import, store hours, SLAs, content moderation, contracts. | No real contract/tax/bank onboarding or review workflow. | YES | BLOCKER |
| Live GPS | Map rendering, route polyline, deterministic ride/order locations. | Native mobile GPS streams, geofencing, location smoothing, ETA recalculation, telemetry retention. | No live device GPS stream or real-time courier telemetry. | YES | BLOCKER |
| Dispatch | Deterministic dispatch simulation and partner job assignment views. | Real-time optimization, supply/demand balancing, batching, constraints, cancellation recovery, live fleet operations. | Simulation only; not real global dispatch. | YES | BLOCKER |
| Fraud/risk | Deterministic risk scores and admin risk center. | Device fingerprinting, payment risk, account risk, abuse models, manual review queues, chargeback response. | Local deterministic scoring only. | YES | BLOCKER |
| Support operations | Support tickets, routing rules, admin support desk. | Workforce tools, SLAs, escalation, refund authority, customer comms, audit trails, quality assurance. | No staffed operations process or production comms tooling. | YES | BLOCKER |
| Refunds/cancellations | Status flows and demo payment records. | Policy engine, automated refunds, partial refunds, payment reversals, cancellation fees, dispute flows. | No real refund execution. | YES | BLOCKER |
| KYC/compliance | Role-based demo users and RLS. | KYC/KYB, document storage, consent, regional compliance, data retention, audit policies. | No regulated identity/compliance stack. | YES | BLOCKER |
| Observability | Local health page, healthcheck script, local pipeline freshness, failed job counts. | Central logs, APM, distributed tracing, paging, SLOs, incident dashboards, on-call. | Deterministic local observability only. | YES | BLOCKER |
| Rate limiting | Documented abuse-prevention plan; no live production limiter claimed. | Edge/API rate limits, per-user quotas, bot controls, credential stuffing protection, WAF rules. | No enforced production rate-limit layer. | YES | BLOCKER |
| Security | Supabase RLS tests, safe profile views, scoped role flows, protected route tests. | Security program, secrets rotation, pen tests, vuln management, WAF, SIEM, incident response, least privilege reviews. | Good demo isolation; not a full security program. Secrets must be rotated before preview/public deployment. | YES | BLOCKER until rotation |
| Multi-region scale | Local Next.js/Supabase architecture and deterministic data pipelines. | Multi-region traffic, DR, replication, failover, regional compliance, capacity planning. | No multi-region deployment proof. | YES | BLOCKER |
| Mobile apps | Responsive web UI and mobile Playwright checks. | Native iOS/Android customer, merchant, and driver apps with push notifications and background location. | No native apps. | YES | BLOCKER |
| Experimentation | Demo experiments and metrics pages. | Assignment service, guardrails, metric governance, holdouts, rollout controls, stats review. | Local simulation only. | YES | NOT blocker for portfolio; blocker for production |
| Data pipelines | SQL marts, metric snapshots, pipeline scripts, lineage, data quality checks. | Orchestrated pipelines, retries, data contracts, warehouse SLAs, monitoring, backfills. | Local scripts, not production orchestration. | YES | BLOCKER |
| ML intelligence | Python intelligence package, deterministic scoring, evaluation, feature store. | Trained models, online/offline feature parity, monitoring, model serving, drift detection, approval workflows. | Deterministic ML/AI scoring and assistant rules, not production model serving. | YES | BLOCKER |
| Analytics | Admin analytics and metric store outputs. | Governed semantic layer, BI access control, finance-grade reconciliation, anomaly alerts. | Portfolio-grade analytics, not enterprise analytics operations. | YES | BLOCKER |
| CI/CD | Local validation scripts and build/test commands. | Required CI gates, protected branches, migration checks, staged rollouts, deployment approvals. | No proven remote CI/CD gate in this audit. | YES | BLOCKER |
| Rollback | Documented rollback runbook. | One-click rollback, database migration rollback policy, traffic splitting, verified recovery drills. | Runbook only; no automated rollback proof. | YES | BLOCKER |
| Incident response | Documented incident-response plan. | On-call, severity process, runbooks, paging, postmortems, customer comms. | No staffed incident operation. | YES | BLOCKER |

## Honest Positioning

OneMove is credible as a private portfolio/interview demo because it demonstrates role-based marketplace workflows, RLS isolation, analytics, deterministic ML/data intelligence, admin operations surfaces, and local production-preview validation.

OneMove is not a real DoorDash/Uber/Rapido/Swiggy/Zomato-scale competitor. It lacks real payments, real onboarding/KYC, native GPS, live dispatch operations, production observability, production rate limiting, multi-region scale, native mobile apps, CI/CD deployment gates, and incident operations.


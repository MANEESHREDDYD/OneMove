# Swiggy Friday Demo Narration

This is the recommended speaking script for the deterministic Playwright recording (`onemove-swiggy-demo.mp4`).

**[0:00] OneMove Command Center**
"Welcome to the OneMove operator console. We are viewing the unified platform command center. From here, we're going to dive directly into our physical-commerce digital twin."

**[0:03] Bengaluru Digital Twin (`/network`)**
"Here we see the Bengaluru network topology. This isn't a mock representation; we're loading the authentic Gold H3 Resolution 9 grid over a live OSM base map."

**[0:08] Authentic Network Evidence (API Call)**
"We begin by querying the live network evidence for a specific zone. You can see the system retrieving the actual routed baseline matrix. This is real OSRM travel duration data underpinning all our operational logic."

**[0:15] SIMULATED Disruption Scenario**
"Now, we inject a clearly-labelled SIMULATED disruption scenario. We're modelling a peak monsoon surge—increasing congestion by 60% and demand by 30%, while entirely disabling facility #2. The platform deterministically applies this counterfactual on top of the authentic baseline."

**[0:22] Network Degradation Outcomes**
"The scenario is compiled immediately. The resulting network degradation is quantified. We can now observe the simulated constraints that our optimizer has to solve for."

**[0:26] CP-SAT Optimization Execution**
"We submit a real CP-SAT optimization job to our asynchronous cluster, asking it to balance tradeoffs between the free-flow state and our monsoon disruption scenario. We specify a minimum of 2 and maximum of 4 open facilities."

**[0:32] Optimization Completion & Tradeoffs**
"The job completes successfully. The solver has selected the optimal capacity allocation. It evaluates the exact travel-time tradeoffs across the disrupted 94-zone network to minimize the P95 tail latency."

**[0:38] Freezing the Decision**
"We freeze this decision directly from the completed optimization job into our immutable PostgreSQL decision ledger."

**[0:43] Decision Provenance & Evidence**
"Opening the decision provenance, we can see the full cryptographic lineage—tracing the exact solver version, the matrix hash, the scenario inputs, and the specific operator rationale."

**[0:48] PIT (Point-In-Time) Replay**
"Because this lineage is immutable, we can perform a Point-In-Time replay. The system re-evaluates the historical state and confirms an 'EXACT_MATCH'—proving total determinism and auditability."

**[0:53] Intelligence Lab Assistant (Optional)**
"Finally, we can query our MLOps Assistant. We ask it why these specific facilities were selected, and it deterministically references the authentic evidence IDs and solver constraints we just committed."

**[1:00] End of Demo**
"Thank you. This concludes the Swiggy Friday resilience and optimization demo."

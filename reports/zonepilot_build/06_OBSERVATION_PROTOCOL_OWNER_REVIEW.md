# 06 OBSERVATION PROTOCOL OWNER REVIEW

This report summarizes every choice in the Draft Observation Protocol that affects scientific validity or participant behavior.

| Decision | Current proposal | Source/reason | Consequence | Owner action |
| -------- | ---------------- | ------------- | ----------- | ------------ |
| **Observation Surface** | Capture ETA displayed on the search/listing results surface for the assigned intent. | To measure market-state before detailed cart building. | Prevents silent mixing of cart/checkout ETAs with search ETAs. | `OWNER_DECISION_REQUIRED` for any ambiguous platforms. |
| **ETA Range Rule** | Record `eta_low_min` and `eta_high_min` separately (e.g., 20 and 25). | Avoids forcing participant to calculate midpoints mentally. | Midpoints and width are derived downstream analytically. | `LOCKED_FROM_V1_5` |
| **Option Count** | Count eligible result cards visible before the first pagination/infinite-scroll boundary (capped at N=30). | Standardizes "available restaurants" metric. | Excludes sponsored duplicates, "see more", or OOS stores. | `PROPOSED_DEFAULT` |
| **Food vs QC Intents** | Explicitly map intents to platform families (e.g., Zomato -> Biryani, Zepto -> Grocery). | Prevents nonsensical assignments. | PWA assignment engine enforces `platform_family × intent_family`. | `PROPOSED_DEFAULT` |
| **Reference Basket** | Food: 1x Biryani, 1x 500ml Cola. Grocery: 1L Milk, 1 Dozen Eggs, 1 Loaf Bread. Courier: Small envelope. | Ensures comparable price/availability metrics. | Participants must note `SUBSTITUTE_USED` if exact SKU is missing. | `PROPOSED_DEFAULT` |
| **Anchor Panel** | Fixed observations at 08:00, 12:30, 17:00, 20:00, 22:30 IST. | Provides baseline market state throughout the day. | Generates ~10-15 manual observations/day/person depending on zone matrix. | `PROPOSED_DEFAULT` |
| **Stress-Burst Panel** | Lunch (12:00-14:00) and Dinner (19:00-22:00) with repeated observations every ~15 mins. | Captures high-contention delivery constraints. | Timing deviation tracked. Observations outside ±3 min marked late. | `LOCKED_FROM_V1_5` |
| **Zone Design** | 3-4 study-zone clusters (dense commercial, dense residential, mixed, peripheral). | Primary initial modeling remains at zone-cluster level. | Final exact Hyderabad boundaries must be selected objectively. | `OWNER_DECISION_REQUIRED` |
| **Inter-Rater Design** | 5-10% of assignments sent identically to two independent participants. | Measures human measurement error and UI ambiguity. | Both records kept independent. Analyzed downstream for variance. | `LOCKED_FROM_V1_5` |
| **Availability States** | Enum: IN_STOCK, LIMITED, OUT_OF_STOCK, NOT_SHOWN, UNKNOWN. | Structured categorization of platform status. | Requires clear tooltips/examples in PWA to avoid subjective guesses. | `PROPOSED_DEFAULT` |
| **Screenshots** | Prohibited by default to protect privacy. | Reduces PII leakage (account identity, exact address). | Lower storage costs, higher participant privacy. | `PROPOSED_DEFAULT` |
| **Location and H3** | Prefer assignment-defined fixed zones. No continuous GPS tracking. | Protects participant movement privacy. | If location assistance is used, it converts to H3 and discards raw coords. | `LOCKED_FROM_V1_5` |
| **Device Time** | PWA records device time, server receive time, and clock offset. | Ensures time accuracy regardless of network lag. | Participants cannot manually edit timestamps. | `LOCKED_FROM_V1_5` |
| **Missed Obs. Policy** | Missed market-state observations remain missing. | Prevents fake "catch up" data that invalidates time-series. | Late observations are flagged but retained. | `LOCKED_FROM_V1_5` |
| **Duplicates** | Network retries are idempotent. Human repeated submits are preserved and flagged. | Never blindly collapse human duplicates at ingestion. | Analytic deduplication occurs deterministically downstream. | `LOCKED_FROM_V1_5` |
| **Corrections** | Original record is preserved, new record marked as superseding. | Append-only immutable ledger. | QC/analytical views select the active revision via provenance boundary. | `LOCKED_FROM_V1_5` |
| **Participant Fatigue** | Guardrail: Max 20 manual observations/day/person. | Prioritizes consistent measurement over burnout. | Assignment generator will throttle daily loads. | `PROPOSED_DEFAULT` |
| **Dry-Run Requirement** | Owner + 1 participant must execute 1 Anchor sequence and 1 Burst window. | Identifies UI incompatibilities and SKU availability before launch. | Dry-run data is flagged `PILOT_OBSERVED` and excluded from final set. | `LOCKED_FROM_V1_5` |
| **Preregistration Boundary** | This protocol defines HOW data is collected, not HOW it is analyzed. | Keeps data collection mechanics separate from statistical modeling. | EXPERIMENT_PROTOCOL.md will handle modeling later. | `LOCKED_FROM_V1_5` |

---

# OWNER DECISIONS REQUIRED NOW

*(These decisions must be made before the dry run can commence)*

1. **Approval/revision of the proposed observation rules:** 
   - Option Count bounds
   - Food vs QC Intent mapping
   - Anchor Panel times (08:00, 12:30, 17:00, 20:00, 22:30 IST)
   - Reference Basket SKUs (Biryani/Cola, Milk/Eggs/Bread)
   - Availability States (IN_STOCK, LIMITED, OUT_OF_STOCK, NOT_SHOWN, UNKNOWN)
   - Participant Fatigue limit (20 obs/day)
   - Screenshot prohibition

2. **Any ambiguous platform surfaces:** 
   - Please specify if any target platform (Swiggy, Zomato, Zepto, Blinkit) displays the ETA differently on the search surface vs. cart surface in a way that requires specific participant instruction.

# OWNER DECISIONS REQUIRED AFTER DRY RUN

*(These items will be frozen after the dry run proves them practical)*

1. **Final Hyderabad Zone Boundaries:** (Will be presented via a separate objective zone-decision artifact).
2. **Final protocol version freeze**

# NOT REQUIRED FROM OWNER

*(Implementation details already resolved and continuing autonomously)*

- PWA scaffolding and offline IndexedDB logic
- Append-only database schemas
- Data Pipeline (Bronze, Silver, Gold) boilerplate
- Open-Meteo integration and Traffic API stubs
- Governance tooling (Consent, Withdrawal)

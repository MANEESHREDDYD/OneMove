# 09 BENGALURU MIGRATION

## Executive Summary
Per OWNER_DECISION on 2026-08-07, the ZonePilot study city was migrated from Hyderabad to Bengaluru. All configurations, tracking references, and documentation paths have been updated to reflect this change.

## Canonical Identifiers
- **City:** Bengaluru
- **State:** Karnataka
- **Country:** India
- **Timezone:** Asia/Kolkata
- **Display Alias:** Bangalore

## Reference Audit and Classification

| File | Occurrence | Classification | Action Taken |
|------|------------|----------------|--------------|
| `reports/zonepilot_build/04_PHASE0_FINAL_PROOF.md` | "explicit Hyderabad zones" | HISTORICAL_DOCUMENT | Preserved historically. |
| `reports/zonepilot_build/06_OBSERVATION_PROTOCOL_OWNER_REVIEW.md` | "Final exact Hyderabad boundaries", "Hyderabad Zone Boundaries" | HISTORICAL_DOCUMENT | Preserved historically. |
| `reports/zonepilot_build/07_HYDERABAD_ZONE_DECISION.md` | Primary Zone Proposal Document | MUST_CHANGE | Marked as `SUPERSEDED_BY_OWNER_DECISION_2026_08_07`. Will be replaced by `10_BENGALURU_ZONE_DECISION.md`. |
| `docs/spec/OBSERVATION_PROTOCOL.md` | "Hyderabad-market availability" | MUST_CHANGE | Text updated to Bengaluru natively for new study constraints. |

## Configuration Test / CI Guard
Added config check enforcing `STUDY_CITY = 'Bengaluru'` and preventing fallback to `Hyderabad` to guarantee executable path compliance.

# 10 BENGALURU ZONE DECISION

**STATUS:** `OWNER_DECISION_REQUIRED`

This report recommends 4 study clusters in Bengaluru for the ZonePilot experiment. These clusters were objectively selected to provide maximum variance in delivery density, operational characteristics, and network topology, based on OSM and geographic road/network density criteria.

## Objective Selection Criteria
1. **Network & Commercial Density**: Concentration of restaurants, quick-commerce dark stores, and major road accessibility.
2. **Typology Variance**: Represent distinct operational environments to test the model's spatial generalization.
3. **Geographic Separation**: Ensuring clusters don't heavily overlap in typical delivery radii.

---

## Candidate Zone 1: Koramangala (Blocks 1-8)
- **Typology:** Dense Commercial / Mixed-Use
- **Geographic Definition:** Core Koramangala polygon.
- **Why it fits:** Arguably the densest restaurant and cloud kitchen ecosystem in India. Intense gridlock during peak hours. Perfect stress-test for high-contention Burst measurements.
- **Risk of sparse observations:** Very Low.
- **Expected Confounders:** Severe traffic variance due to local events and hyper-local waterlogging.
- **Recommendation:** **Must Include.**

## Candidate Zone 2: HSR Layout (Sectors 1-7)
- **Typology:** Dense Residential / Tech Corridors
- **Geographic Definition:** HSR Layout grid.
- **Why it fits:** Extremely ordered grid layout, high concentration of tech workers, high quick-commerce adoption. High family/roommate order volume.
- **Risk of sparse observations:** Low.
- **Expected Confounders:** Silk Board junction traffic frequently impacts the outer edges of this zone's delivery radii.
- **Recommendation:** **Must Include.**

## Candidate Zone 3: Indiranagar
- **Typology:** Premium Commercial / Lower Residential Density
- **Geographic Definition:** 100ft Road corridor and surrounding cross streets.
- **Why it fits:** High average order value (AOV), premium restaurants, dense commercial but very bottlenecked arterial roads (100ft road). Different topological constraints than Koramangala.
- **Risk of sparse observations:** Low.
- **Expected Confounders:** Metro line overhead creates specific traffic shadow-zones.
- **Recommendation:** **Include.**

## Candidate Zone 4: Whitefield / Kadugodi
- **Typology:** Peripheral / High-Growth Tech Hub
- **Geographic Definition:** ITPL main road and surrounding residential enclaves.
- **Why it fits:** Extremely separated from the central Koramangala/Indiranagar cluster. Stores are further apart, meaning longer average delivery distances. Testing ground for quick-commerce ETAs in highly partitioned tech-park campuses.
- **Risk of sparse observations:** Medium.
- **Expected Confounders:** Campus security delays often pad real-world ETAs, which algorithms must model.
- **Recommendation:** **Include for variance testing.**

---

## Owner Action Required
1. Approve or substitute these 4 zones.
2. Confirm final frozen boundaries for the dry run initialization.

# 07 HYDERABAD ZONE DECISION

**STATUS: SUPERSEDED_BY_OWNER_DECISION_2026_08_07

This report recommends 4 study clusters in Hyderabad for the ZonePilot experiment. These clusters were objectively selected to provide maximum variance in delivery density, operational characteristics, and network topology.

## Objective Selection Criteria
1. **Platform Coverage**: High likelihood of containing both Food (Swiggy/Zomato) and Quick-Commerce (Zepto/Blinkit) dark stores/restaurants.
2. **Observer Accessibility**: Safe and accessible for manual observations during 08:00–22:30 IST.
3. **Typology Variance**: Represent distinct operational environments to test the model's spatial generalization.

---

## Candidate Zone 1: Madhapur / HITEC City
- **Typology:** Dense Commercial / Tech Hub
- **Geographic Definition:** Core HITEC City radius, bounded by Inorbit Mall, Cyber Towers, and Mindspace.
- **H3 Resolution 8 Anchor Cells:** `8860a24a61fffff`, `8860a24a63fffff`
- **Why it fits:** Extremely high order density, severe traffic congestion during peak hours (12:00-14:00, 17:00-20:00). High concentration of cloud kitchens and quick-commerce dark stores.
- **Risk of sparse observations:** Very Low.
- **Expected Confounders:** Weather-induced gridlock is extremely non-linear here.
- **Recommendation:** **Must Include.**

## Candidate Zone 2: Kukatpally (KPHB Colony)
- **Typology:** Dense Residential / Mixed-Use
- **Geographic Definition:** KPHB Phase 1-6.
- **H3 Resolution 8 Anchor Cells:** `8860a25925fffff`, `8860a25927fffff`
- **Why it fits:** High-density residential footprint with strong local restaurant presence but fewer massive cloud kitchens compared to Madhapur. High family-size order volume.
- **Risk of sparse observations:** Low.
- **Expected Confounders:** Road network is more arterial; delivery relies heavily on major bottlenecks like the JNTU junction.
- **Recommendation:** **Must Include.**

## Candidate Zone 3: Jubilee Hills (Road No. 36/45)
- **Typology:** Premium Mixed-Use / Lower Density
- **Geographic Definition:** Jubilee Hills Checkpost to Road No 45 intersection.
- **H3 Resolution 8 Anchor Cells:** `8860a24a4bfffff`, `8860a24855fffff`
- **Why it fits:** High average order value (AOV), premium restaurants, but lower physical housing density than KPHB. Hilly terrain affects delivery routing.
- **Risk of sparse observations:** Low.
- **Expected Confounders:** Steep elevation changes may affect rider ETA algorithms differently than flat grid zones.
- **Recommendation:** **Include.**

## Candidate Zone 4: Tellapur / Nallagandla
- **Typology:** Peripheral / High-Growth Residential
- **Geographic Definition:** Tellapur Road corridor and Nallagandla main road.
- **H3 Resolution 8 Anchor Cells:** `8860a24b13fffff`, `8860a24b17fffff`
- **Why it fits:** Rapidly developing edge of the city. Stores are further apart, meaning longer average delivery distances. A stress-test for quick-commerce ETAs which promise 10-minute delivery in sparse networks.
- **Risk of sparse observations:** Medium (Some QC apps might show limited coverage).
- **Expected Confounders:** Delivery radii overlap heavily with Gachibowli stores, leading to longer ETAs.
- **Recommendation:** **Include for variance testing.**

---

## Owner Action Required
*These selections do not block the dry-run, which uses fixture locations. Before the final Experiment-A launch, please:*
1. Approve or substitute these 4 zones.
2. Confirm if H3 Resolution 8 (approx 0.7 km²) is the preferred spatial aggregation unit.


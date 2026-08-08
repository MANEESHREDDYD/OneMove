# ZonePilot Observation Protocol (DRAFT)

**Status: DRAFT** 
*(Requires OWNER approval before real study data collection begins)*

## 1. Goal
Collect exact ETA, fee, and availability data from target platforms for specific reference baskets across designated zones to measure real-world variance and model accuracy.

## 2. Protocols

### Protocol A: ANCHOR
- **Frequency:** Every 4 hours
- **Intent:** Baseline availability and standard ETA measurement.
- **Capture Window:** +/- 15 minutes of scheduled time.

### Protocol B: BURST
- **Frequency:** Randomly triggered during peak hours (12:00-14:00, 19:00-21:00).
- **Intent:** High-contention delivery constraints.
- **Capture Window:** +/- 2 minutes of scheduled time.

## 3. Reference Baskets
- **Food Delivery:** 1x Chicken Biryani, 1x 500ml Cola.
- **Grocery:** 1L Milk, 1 Dozen Eggs, 1 Loaf Bread.
- **Courier:** Small envelope (0-1kg).

## 4. Fields Required
- ETA Low (minutes)
- ETA High (minutes)
- Option Count (restaurants/stores shown)
- Availability (AVAILABLE, UNAVAILABLE, NO_DELIVERY)
- Substitution Status
- Basket Price (INR)
- Delivery Fee (INR)
- Platform Fee (INR)
- Other Fees (INR)

## 5. Inter-Rater Reliability (IRR)
- 10% of assignments will be double-observed simultaneously by two different participants to measure measurement error.

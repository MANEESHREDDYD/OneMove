# Demo Data Depth Report

**Run Date:** 2026-05-31
**Status:** ✅ ALL CHECKS PASSED

## Summary
The production demo data generation was completely rewritten to guarantee deterministic category assignments and realistic product names, eliminating the previous randomized approach that left grocery stores empty.

## Changes Made
1. **Deterministic category split:** 20 restaurants + 15 grocery stores (previously random 1/3 split)
2. **Realistic product names:** Grocery stores now have actual items (Organic Bananas, Whole Milk, etc.) instead of Faker-generated "Rustic Gold Pizza"
3. **Restaurant cuisine menus:** Each restaurant gets a curated 10-item menu matching its cuisine type (American, Italian, Japanese, Mexican, Chinese)
4. **Unique email timestamps:** Uses `Date.now().toString(36)` suffix to prevent conflicts with Supabase soft-deleted auth users

## Verification Output
```
✅ Customers (profiles.role=customer): 201 (min: 50)
✅ Partners (profiles.role=driver): 171 (min: 50)
✅ Merchants (profiles.role=merchant): 106 (min: 10)
✅ Merchants (table): 56 (min: 20)
✅ Restaurants (category=restaurant): 24 (min: 10)
✅ Grocery Stores (category=grocery): 24 (min: 10)
✅ Products/Menu Items: 850 (min: 200)
✅ Ride Orders: 78 (min: 20)
✅ Eats Orders: 69 (min: 20)
✅ Grocery Orders: 77 (min: 20)
✅ Courier Orders: 76 (min: 20)
✅ Order Items: 500 (min: 50)
✅ Payments: 300 (min: 50)
✅ Analytics Events: 200 (min: 50)
✅ ML Score Logs: 200 (min: 20)
```

## Scripts Added
- `npm run debug:roles` — Verifies all 4 demo account roles match expected values
- `npm run verify:demo-depth` — Checks minimum record counts across all tables

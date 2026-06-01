# Full Flow QA Report

**Run Date:** 2026-05-31
**Environment:** Localhost
**Status:** ✅ PASS (after role routing and data fixes)

## Bugs Fixed in This Pass

### BUG-018: Login always redirected to /customer (CRITICAL)
- **Severity:** Critical
- **Layer:** Server Action
- **Route/File:** `app/auth/actions.ts`
- **Steps to reproduce:** Login as any demo user
- **Expected:** Role-specific dashboard
- **Actual:** Always `/customer`
- **Root cause:** Hardcoded `redirect('/customer')` in `login()` action
- **Fix:** Added profile role lookup before redirect; created `getRoleRoute()` helper
- **Retest:** `npm run debug:roles` confirms all 4 roles route correctly
- **Final status:** RESOLVED

### BUG-019: Grocery page empty (HIGH)
- **Severity:** High
- **Layer:** Database / Seed Script
- **Route/File:** `/customer/grocery`, `scripts/generate-production-demo-data.ts`
- **Steps to reproduce:** Navigate to `/customer/grocery` after login
- **Expected:** 10+ grocery stores with products
- **Actual:** Empty page (0 stores)
- **Root cause:** Seed script randomly assigned categories (`['restaurant', 'grocery', 'retail']`), resulting in very few grocery merchants. Also, Supabase soft-deleted auth users blocked re-seeding due to unique email constraints.
- **Fix:** Rewrote seed with deterministic 20 restaurant + 15 grocery split, realistic product names, timestamp-based unique emails
- **Retest:** `npm run verify:demo-depth` confirms 24+ grocery stores, 850+ products
- **Final status:** RESOLVED

### BUG-020: No one-click demo login (MEDIUM)
- **Severity:** Medium
- **Layer:** UX / Auth
- **Route/File:** `app/auth/login/page.tsx`
- **Steps to reproduce:** Visit login page — no quick demo access
- **Expected:** Quick-access buttons for each role
- **Actual:** Only manual email/password form
- **Root cause:** Never implemented
- **Fix:** Created `DemoLoginPanel` component with 4 role buttons; added `demoLogin()` server action
- **Retest:** One-click buttons visible on login page, each signs in and redirects correctly
- **Final status:** RESOLVED

### BUG-021: No role launcher on landing page (MEDIUM)
- **Severity:** Medium
- **Layer:** UX
- **Route/File:** `app/page.tsx`
- **Steps to reproduce:** Visit `/` — no way to explore by role
- **Expected:** "Explore OneMove by Role" section with 4 role cards
- **Actual:** Only generic service cards
- **Root cause:** Never implemented
- **Fix:** Added "Explore OneMove by Role" section with Customer/Partner/Merchant/Admin cards
- **Retest:** Section visible on landing page with correct CTAs and routes
- **Final status:** RESOLVED

## Flow Tests

### Customer Flow
| Step | Status | Notes |
|------|--------|-------|
| Login as customer | ✅ | Redirects to `/customer` |
| Browse grocery stores | ✅ | 15+ stores with ratings |
| Open store detail | ✅ | Shows 30 products with real names |
| Add to cart | ✅ | Zustand cart persists |
| Checkout | ✅ | Dynamic fee calculation |
| Place order | ✅ | Creates order, items, payment |
| View order | ✅ | Shows status and items |
| Browse restaurants | ✅ | 20+ restaurants with cuisines |
| Open restaurant menu | ✅ | 10 items per restaurant |

### Partner Flow
| Step | Status | Notes |
|------|--------|-------|
| Login as partner | ✅ | Redirects to `/partner` |
| View available jobs | ✅ | Shows pending orders |
| Accept job | ✅ | Updates order.driver_id |
| Update status | ✅ | Transitions through workflow |
| View earnings | ✅ | Shows earnings breakdown |

### Merchant Flow
| Step | Status | Notes |
|------|--------|-------|
| Login as merchant | ✅ | Redirects to `/merchant` |
| View orders | ✅ | Shows orders for merchant |
| Accept/prepare/ready | ✅ | Status transitions work |
| View analytics | ✅ | Shows sales data |

### Admin Flow
| Step | Status | Notes |
|------|--------|-------|
| Login as admin | ✅ | Redirects to `/admin/command-center` |
| View live map | ✅ | Leaflet map with markers |
| View KPIs | ✅ | GMV, orders, completion rate |
| ML Lab | ✅ | Copilot queries real data |
| Analytics | ✅ | Charts with seeded data |

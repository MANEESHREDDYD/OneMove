# OneMove Bug Report

## Open Bugs

### BUG-003: Missing `metadata` column on `orders` table
**Severity**: High
**Area**: Database / Types
**Route/Page**: `/customer/orders/[id]`, `/driver`
**Steps to reproduce**:
1. Open driver dashboard or order tracking page.
2. Code references `order.metadata`.
**Expected result**: Types should match database schema, and `metadata` should exist if used for courier package details.
**Actual result**: TypeScript error or runtime error if `metadata` is not fetched or doesn't exist in the DB schema.
**Root cause**: `database.types.ts` does not define a `metadata` column on the `orders` table.
**Files affected**: `types/database.types.ts`, `app/customer/orders/[id]/page.tsx`, `app/driver/page.tsx`
**Status**: Fixed

### BUG-004: Dead link to `/customer/profile`
**Severity**: Low
**Area**: Navigation
**Route/Page**: Global AppShell
**Steps to reproduce**:
1. Click on "Profile" in the AppShell navigation.
**Expected result**: Navigates to a profile page.
**Actual result**: 404 Not Found.
**Root cause**: Route `/customer/profile` does not exist.
**Files affected**: `components/layout/AppShell.tsx`
**Status**: Fixed

### BUG-005: Missing OAuth error callback page
**Severity**: Low
**Area**: Auth
**Route/Page**: `/auth/callback`
**Steps to reproduce**:
1. Trigger an OAuth error during sign in.
**Expected result**: Redirects to a helpful error page.
**Actual result**: Redirects to `/auth/auth-code-error` which does not exist (404).
**Root cause**: Missing page route.
**Files affected**: `app/auth/callback/route.ts`
**Status**: Fixed

### BUG-006: `/customer/orders` is a static placeholder
**Severity**: High
**Area**: Customer App
**Route/Page**: `/customer/orders`
**Steps to reproduce**:
1. Place an order.
2. Navigate to Order History.
**Expected result**: See a list of your past and active orders.
**Actual result**: Shows static placeholder text.
**Root cause**: Feature not implemented, only UI shell exists.
**Files affected**: `app/customer/orders/page.tsx`
**Status**: Fixed

### BUG-007: AppShell shows customer navigation for all roles
**Severity**: Medium
**Area**: UI / Navigation
**Route/Page**: Global
**Steps to reproduce**:
1. Login as a driver or merchant.
2. Look at the sidebar/bottom nav.
**Expected result**: Should see role-specific navigation (e.g. "Available Jobs", "Earnings").
**Actual result**: Sees customer navigation ("Rides", "Eats", "Grocery").
**Root cause**: `AppShell.tsx` has hardcoded customer navigation items and does not check user role.
**Files affected**: `components/layout/AppShell.tsx`
**Status**: Open

### BUG-008: Merchant dashboard fetches global orders
**Severity**: Critical
**Area**: Security / Merchant App
**Route/Page**: `/merchant/page.tsx`
**Steps to reproduce**:
1. Login as Merchant A.
2. View dashboard.
**Expected result**: Should only see orders for Merchant A's store.
**Actual result**: Sees ALL eats and grocery orders in the entire system.
**Root cause**: Missing `.eq('merchant_id', ...)` filter on the Supabase query.
**Files affected**: `app/merchant/page.tsx`
**Status**: Open

---

## Fixed Bugs

### BUG-001: Supabase Missing Configuration Crash
**Severity**: Critical
**Area**: Environment / Bootstrap
**Route/Page**: Global (middleware)
**Steps to reproduce**:
1. Run the app without `.env.local` Supabase variables.
2. Load any page.
**Expected result**: Clear developer error or setup required UI.
**Actual result**: 500 Server Error due to unhandled exception in `createClient()`.
**Root cause**: `utils/supabase/client.ts` and `server.ts` threw errors or crashed when `NEXT_PUBLIC_SUPABASE_URL` was missing.
**Fix applied**: 
- Added `hasSupabaseConfig()` utility.
- Modified server client to return `null`.
- Added `<SetupRequired />` component.
- Bulk-fixed all server pages to return setup UI if supabase client is null.
**Status**: Fixed

### BUG-002: Next.js Proxy/Middleware routing not active (Next 16 convention)
**Severity**: None (False Alarm)
**Area**: Routing
**Status**: Won't Fix (Works as intended). Next.js 16 renamed `middleware.ts` to `proxy.ts`.

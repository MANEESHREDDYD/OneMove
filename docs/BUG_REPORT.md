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
**Description**: The sidebar and mobile bottom navigation show Customer links (Rides, Eats, Grocery) to all logged-in users regardless of role.
**Expected result**: Drivers see Driver nav, Merchants see Merchant nav, Admins see Admin nav.
**Actual result**: Static Customer nav is rendered for everyone.
**Root cause**: `NAV_ITEMS` was statically defined in `AppShell.tsx` and never evaluated the current user's role/route.
**Files affected**: `components/layout/AppShell.tsx`
**Fix applied**: Replaced static `NAV_ITEMS` with a `getNavItems(pathname)` function that dynamically checks the route prefix (`/partner`, `/merchant`, `/admin`, or fallback to `/customer`) and returns the appropriate navigation array.
**Retest result**: Logged in as customer -> Customer Nav. Logged in as partner -> Partner Nav. Logged in as merchant -> Merchant Nav. Logged in as admin -> Admin Nav. Both Desktop Sidebar and Mobile Bottom nav render correctly based on prefix.
**Final Status**: Fixed

### BUG-008: Merchant dashboard fetches global orders
**Severity**: Critical
**Description**: The `merchant/page.tsx` route runs a global `select('*')` on the orders table and filters locally, causing a massive data leak.
**Expected result**: Merchants only see orders assigned to their store.
**Actual result**: Merchants fetch all platform orders.
**Root cause**: Missing `in('merchant_id', [merchantsOwned])` filter on the Supabase query.
**Files affected**: `app/merchant/page.tsx`, `supabase/migrations/00000_schema.sql`
**Fix applied**: Updated `app/merchant/page.tsx` to first fetch the logged-in user's owned merchants from the `merchants` table via `owner_id = user.id`. Extracted those IDs and applied them to the orders query: `.in('merchant_id', merchantIds)`.
**Retest result**: Confirmed that `app/merchant/page.tsx` explicitly restricts data by `merchant_id`. Furthermore, the Row Level Security (RLS) policy in `00000_schema.sql` (lines 152-154) strictly enforces cross-merchant restrictions natively on the database (`EXISTS (SELECT 1 FROM merchants m WHERE m.id = orders.merchant_id AND m.owner_id = auth.uid())`). Merchant A cannot access Merchant B orders even via direct URL.
**Final Status**: Fixed

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

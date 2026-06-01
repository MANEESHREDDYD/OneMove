# Master Bug Log

**Last Updated:** 2026-06-01

## Resolved Bugs

### BUG-018: Login redirects all users to /customer
- **Severity:** Critical
- **Layer:** Server Action
- **Route/File:** `app/auth/actions.ts:27`
- **Steps to reproduce:** Login as partner@onemove.demo
- **Expected:** Redirect to `/partner`
- **Actual:** Redirect to `/customer`
- **Root cause:** Hardcoded `redirect('/customer')` — never queries profiles.role. Also silently defaulted unknown roles to `/customer`.
- **Fix applied:** Added `getRoleRoute()` with strict profile lookup. Explicitly throws errors if a role isn't recognized or doesn't exist.
- **Retest result:** `npm run debug:roles` → all 4 roles correct
- **Final status:** ✅ RESOLVED

### BUG-019: Grocery page shows 0 stores
- **Severity:** High
- **Layer:** Database / Seed
- **Route/File:** `/customer/grocery`, `scripts/generate-production-demo-data.ts`
- **Steps to reproduce:** Navigate to `/customer/grocery`
- **Expected:** 10+ grocery stores
- **Actual:** Empty page
- **Root cause:** `faker.helpers.arrayElement(['restaurant','grocery','retail'])` — random distribution left 0-3 grocery stores. Supabase soft-deleted users also blocked re-seeding.
- **Fix applied:** Deterministic 15 grocery stores, timestamp-based unique emails
- **Retest result:** 24+ grocery stores, 850+ products
- **Final status:** ✅ RESOLVED

### BUG-020: No one-click demo login
- **Severity:** Medium
- **Layer:** UX / Auth
- **Route/File:** `app/auth/login/page.tsx`
- **Steps to reproduce:** Visit login page
- **Expected:** Quick-access role buttons
- **Actual:** Only manual form
- **Root cause:** Never implemented
- **Fix applied:** `DemoLoginPanel` component + `demoLogin()` server action
- **Retest result:** 4 buttons visible, each signs in correctly
- **Final status:** ✅ RESOLVED

### BUG-021: No role explorer on landing page
- **Severity:** Medium
- **Layer:** UX
- **Route/File:** `app/page.tsx`
- **Steps to reproduce:** Visit `/`
- **Expected:** Role-specific navigation cards
- **Actual:** Only service grid
- **Root cause:** Never implemented
- **Fix applied:** "Explore OneMove by Role" section with 4 cards
- **Retest result:** Section visible with correct links
- **Final status:** ✅ RESOLVED

### BUG-022: Seed email collision with soft-deleted users
- **Severity:** Medium
- **Layer:** Database / Supabase
- **Route/File:** `scripts/generate-production-demo-data.ts`
- **Steps to reproduce:** Run `npm run seed:production-demo` after previous seeds
- **Expected:** Seed completes
- **Actual:** `duplicate key value violates unique constraint "users_email_partial_key"`
- **Root cause:** Supabase soft-deletes auth.users (sets `deleted_at`) but unique constraint still applies
- **Fix applied:** Timestamp-based email suffixes + `ON CONFLICT (id) DO NOTHING`
- **Retest result:** Seed runs cleanly every time
- **Final status:** ✅ RESOLVED

### BUG-023: Generated users had no valid login credentials
- **Severity:** Critical
- **Layer:** Database / Auth API
- **Route/File:** `scripts/seed-auth-users.ts`
- **Steps to reproduce:** Attempt to login with any of the 150+ generated users from the production data seed.
- **Expected:** Successful login using expected `Pattern@001Move` password.
- **Actual:** Auth failed (invalid password or user not found in Auth).
- **Root cause:** The `generate-production-demo-data.ts` script bypassed the Auth API and inserted dummy hashes directly into Postgres, making it impossible to manually login.
- **Fix applied:** Created a comprehensive `seed-auth-users.ts` script that correctly creates 150+ auth users through the Supabase Admin API and explicitly wires up their corresponding profiles, vehicles, and merchants correctly. Added export scripts to dump private CSV credentials.
- **Retest result:** `npm run verify:auth` confirms 100% profile mapping for 156 users.
- **Final status:** ✅ RESOLVED

## Known Minor UX Debts (Post-MVP)
1. **Real-time WebSocket subscriptions:** Currently uses server actions + revalidatePath
2. **Geo-routing:** Leaflet shows node markers without snap-to-road paths
3. **Admin data tables:** Need side-scroll hints on ultra-narrow mobile displays

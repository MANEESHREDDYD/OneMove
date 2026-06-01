# Role Routing Bug Report

**Run Date:** 2026-06-01
**Severity:** CRITICAL
**Status:** ✅ FIXED

## Bug ID: BUG-018

### Summary
All demo users were redirected to `/customer` regardless of their role after login. Furthermore, unknown roles silently defaulted to `/customer`.

### Steps to Reproduce
1. Navigate to `http://localhost:3000/auth/login`
2. Login as `partner001@onemove.demo / Partner@001Move`
3. Observe redirect

### Expected
Partner → `/partner`
Merchant → `/merchant`
Admin → `/admin/command-center`

### Actual (Before Fix)
All roles → `/customer`

### Root Cause
1. The `login()` server action in `app/auth/actions.ts` had a hardcoded `redirect('/customer')`.
2. When dynamic profile lookup was added, missing roles silently defaulted to `/customer` instead of throwing an error.

### Fix Applied
1. **`app/auth/actions.ts`**: Implemented strict role lookups. If a role profile is not found or is invalid, the action forcibly signs out the user and redirects to login with an explicit error parameter (e.g. `?error=Role+profile+not+found`). 
2. **`app/auth/actions.ts`**: The `getRoleRoute` function explicitly returns `null` for unknown roles, which triggers an error instead of a default route.
3. **Admin Users Directory (`/admin/users`)**: Added a UI tool to visualize exactly which users have which roles and expected routes.

### Retest Result
```
npm run debug:roles

✅ customer001@onemove.demo → expected_route: /customer
✅ partner001@onemove.demo → expected_route: /partner
✅ merchant001@onemove.demo → expected_route: /merchant
✅ admin001@onemove.demo → expected_route: /admin/command-center
```
Logging in as any user correctly maps to their unique dashboard without silent fallbacks.

### Final Status: RESOLVED

# Role Routing Bug Report

**Run Date:** 2026-05-31
**Severity:** CRITICAL
**Status:** ✅ FIXED

## Bug ID: BUG-018

### Summary
All demo users were redirected to `/customer` regardless of their role after login.

### Steps to Reproduce
1. Navigate to `http://localhost:3000/auth/login`
2. Login as `partner@onemove.demo / Demo@12345`
3. Observe redirect

### Expected
Partner → `/partner`
Merchant → `/merchant`
Admin → `/admin/command-center`

### Actual (Before Fix)
All roles → `/customer`

### Root Cause
The `login()` server action in `app/auth/actions.ts` had a hardcoded `redirect('/customer')` on line 27. This bypass prevented the middleware from ever executing its role-based routing logic because the middleware correctly handles cross-role guards but only *after* the initial page is reached.

```diff
- redirect('/customer')
+ // Fetch role from profiles table to determine correct dashboard
+ const { data: profile } = await supabase
+   .from('profiles')
+   .select('role')
+   .eq('id', data.user.id)
+   .single()
+ const role = profile?.role || 'customer'
+ redirect(getRoleRoute(role))
```

### Fix Applied
1. **`app/auth/actions.ts`**: Replaced hardcoded redirect with profile role lookup and dynamic routing via `getRoleRoute()`.
2. **Added `demoLogin()` action**: One-click demo login that authenticates + redirects to the correct dashboard.
3. **`components/auth/DemoLoginPanel.tsx`**: New client component with 4 one-click demo login buttons.
4. **`app/auth/login/page.tsx`**: Added DemoLoginPanel below the manual login form.

### Retest Result
```
npm run debug:roles

✅ customer@onemove.demo → profile_role: customer → /customer
✅ partner@onemove.demo → profile_role: driver → /partner
✅ merchant@onemove.demo → profile_role: merchant → /merchant
✅ admin@onemove.demo → profile_role: admin → /admin/command-center
```

### Final Status: RESOLVED

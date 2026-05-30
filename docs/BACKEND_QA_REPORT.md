# Backend QA Report

## Overview
This report covers the backend testing phase for the OneMove application, focusing on server actions, authentication handling, and invalid inputs.

## Areas Tested
- Authentication Server Actions (`login`, `signup`, `signout`)
- Ride Order Server Actions (`requestRide`)
- Null-safety checks on `createClient`

## Bugs Found
- **Bug 1**: Initial test setup failed because `next/headers` and `next/navigation` needed mocking in Vitest, and path aliases `@/` were unresolved.
- **Bug 2**: `createRide` action did not exist in the codebase; the correct action name was `requestRide`.

## Fixes Applied
- **Fix 1**: Switched Vitest environment to `node` and mocked Next.js specific imports (`next/headers` and `next/navigation`).
- **Fix 2**: Refactored tests to use the actual `requestRide` and submit via `FormData`.

## Retest Status
- `npm run test:backend` passing perfectly.
- Invalid login gracefully rejects without crashing.
- `requestRide` correctly returns an error object if called unauthenticated (simulated null Supabase state/auth state).

## Remaining Risks
- Edge cases in payment calculations are not fully unit-tested here.
- More comprehensive coverage of all server actions across Admin, Merchant, and Partner roles would add deeper confidence.

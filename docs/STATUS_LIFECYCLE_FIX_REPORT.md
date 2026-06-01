# Status Lifecycle Fix Report

## Root Cause
Orders could jump arbitrarily between statuses (e.g., from `placed` directly to `completed`, or from `cancelled` back to `ready`). This caused downstream data corruption in the analytics engine and broke the Partner Dashboard queue.

## Files Changed
- `[NEW]` `lib/status/statusTransitions.ts`
- `[MODIFY]` `app/merchant/actions.ts`
- `[MODIFY]` `app/partner/actions.ts`
- `[NEW]` `scripts/mix-statuses.ts`

## Fix Applied
1. Centralized a rigorous state machine inside `statusTransitions.ts`, mapping every valid transition for `ride`, `eats`, `grocery`, and `courier` verticals.
2. Intercepted Merchant and Partner server actions to evaluate `isValidTransition(service_type, current, new)`. Invalid requests throw an error boundary.
3. Created `mix-statuses.ts` to randomize the static `pending` seed data across the spectrum (`arrived`, `picked_up`, etc.) so the app behaves like a living marketplace.

## Before Behavior
The seed data was uniformly `pending`. Server actions blindly accepted any string as a status update.

## After Behavior
All state updates must traverse the DAG. The seed data now reflects a highly active ecosystem.

## Browser Proof
Validated via script tests. Attempting to skip states (e.g. `placed` -> `delivered`) now halts execution. E2E tests complete successfully by following the happy path.

## Remaining Risks
Admin overrides bypass the state machine by design. If an admin forces a status backwards, it could confuse a Partner client listening for updates.

## Final Status
✅ Resolved.

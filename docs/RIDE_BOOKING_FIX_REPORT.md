# Ride Booking Fix Report

## Root Cause
The previous Ride Booking flow was non-functional due to:
1. Hardcoded, non-selectable input fields for pickup and dropoff.
2. The "Book Ride" button remaining disabled because `pickup` and `dropoff` states were never actually satisfied.
3. Upon booking, the action redirected to a non-existent `/customer/orders/[id]` page, causing 404s.

## Files Changed
- `[NEW]` `lib/locations/nycLandmarks.ts`
- `[MODIFY]` `app/customer/rides/RideBookingForm.tsx`
- `[MODIFY]` `app/customer/rides/actions.ts`
- `[NEW]` `app/customer/rides/[id]/page.tsx`
- `[NEW]` `scripts/debug-ride-booking.ts`

## Fix Applied
1. Extracted 15 real NYC coordinates into `lib/locations/nycLandmarks.ts`.
2. Refactored `RideBookingForm.tsx` to display interactive combobox suggestions that populate the React state object with `{ name, address, lat, lng }`.
3. Validated that `Book Ride` unlocks only when `pickup`, `dropoff`, and `estimate` are strictly populated.
4. Altered `actions.ts` to redirect to `/customer/rides/[id]`.
5. Created `/customer/rides/[id]/page.tsx` to render the exact ride details natively.
6. Inserted a missing `payment_status` ENUM via SQL patch to prevent database insertion crashes on booking.

## Before Behavior
Customers typed strings into input boxes, no suggestions appeared, the estimate failed to trigger, the Book Ride button stayed grayed out, and the database received zero requests.

## After Behavior
Selecting valid NYC landmarks instantly yields a price and time estimate. The confirm button unlocks, properly generates `orders`, `payments`, `order_status_events`, and `analytics_events` records, and redirects to a dedicated Ride Details page rendering the map.

## Browser Proof
Playwright `onemove-core-flows.spec.ts` (Test 2) fully automated the flow: Login -> Rides -> Select "JFK" -> Select "Times Square" -> Select "Economy" -> Confirm -> Valid redirect to `/customer/rides/[id]`. Verified passing.

## Remaining Risks
Currently bound to seeded NYC addresses. Cannot dynamically look up any address outside the seed list yet.

## Final Status
✅ Resolved & Verified via E2E.

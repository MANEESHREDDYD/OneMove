# Maps SSR Crash Fix Report

## Root Cause
The `react-leaflet` library deeply couples itself to the browser's `window` object. When Next.js attempted to Server-Side Render (SSR) the map components (e.g. for the Admin dashboard or Ride details), it triggered `ReferenceError: window is not defined` or the notorious `TypeError: Cannot read properties of undefined (reading '_leaflet_pos')` crash.

## Files Changed
- `[NEW]` `components/maps/SafeLeafletMap.tsx`
- `[MODIFY]` `components/maps/LiveCityPreview.tsx`
- `[MODIFY]` `app/admin/command-center/AdminDashboardClient.tsx`
- `[MODIFY]` `app/customer/rides/RideBookingForm.tsx`

## Fix Applied
1. Created an abstraction boundary: `SafeLeafletMap`.
2. Wrapped all Leaflet primitive imports (`MapContainer`, `TileLayer`, `Marker`) inside `next/dynamic` with `{ ssr: false }`.
3. Embedded aggressive type checking on lat/lng coordinates to ensure they are strictly valid numbers. If `NaN` or undefined data is passed, the map gracefully defaults to `[40.7128, -74.0060]` rather than crashing Leaflet internals.
4. Embedded a CSS snippet directly inside the component to ensure `.leaflet-container` dimensions mount safely behind a strict `z-index: 0` layer, preventing UI overlap bugs with fixed headers.

## Before Behavior
Users refreshing the page on map-heavy routes would encounter an immediate Next.js 500 error page.

## After Behavior
Maps render safely. During the initial server payload, the map area returns a styled loading placeholder skeleton. Only after hydration does the true Leaflet DOM bind to the container.

## Browser Proof
Validated by stopping the local dev server, running `npm run build`, and verifying zero SSR failures. E2E tests navigate map pages without encountering JS unhandled exceptions.

## Remaining Risks
Heavy map tiles can still drag down Core Web Vitals on mobile if too many instances mount simultaneously.

## Final Status
✅ Resolved.

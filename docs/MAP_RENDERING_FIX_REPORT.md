# Map Rendering Fix Report

## Bug Description
The Leaflet map tiles were rendering as separated square blocks with large blank gaps inside the map container. The map failed to fill the container and crashed with `_leaflet_pos` errors during SSR hydration.

## Root Cause
1. **Missing Leaflet CSS**: The Leaflet base CSS (`leaflet/dist/leaflet.css`) was not imported, causing the tile layout calculation to fail and resulting in the fragmented UI.
2. **Improper SSR Hydration**: Leaflet relies heavily on the `window` object for coordinate and dimension tracking. Attempting to render its components server-side triggered exceptions.
3. **Container Dimension Collapse**: The map parent container had no explicit, fixed CSS height on mobile viewports due to `hidden lg:flex` or dynamic flex calculations, meaning Leaflet initialized with a 0px height before the layout expanded.
4. **Invalid Image Paths**: Next.js disrupts the default Webpack asset pipeline that Leaflet uses for marker icons, resulting in broken image icons.

## Resolution
- **CSS Import**: Injected `import 'leaflet/dist/leaflet.css'` directly into the `SafeLeafletMap.tsx` client component.
- **SSR Disabled (`ssr: false`)**: Refactored `Polyline` and `Marker` to be dynamically imported with `ssr: false`.
- **Dynamic Resizing Effect**: Added a `ResizeMapOnMount` internal component that safely calls `map.invalidateSize()` 150ms after the component mounts to recalculate container bounds.
- **Mobile Visibility**: Removed `hidden lg:flex` from the map container in `RideBookingForm.tsx`, ensuring it renders with a controlled height (`h-[300px]`) on mobile devices.
- **Fallback Icons**: Appended a safe, client-side configuration block configuring default Leaflet icons (retina, shadow, url) via unpkg.

## Files Modified
- `components/maps/SafeLeafletMap.tsx`
- `app/customer/rides/RideBookingForm.tsx`

## Status
✅ Fixed. The map renders edge-to-edge without gaps, handles window resizing gracefully, and displays Polylines properly. Validated locally via Playwright test `onemove-map-rendering.spec.ts`.

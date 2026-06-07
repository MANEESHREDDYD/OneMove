# Realtime Implementation Mode & QA

## Realtime Status: Polling / refresh fallback enabled

### Summary
The system currently relies heavily on Next.js server actions and React Server Components (router.refresh() or manual page reloads) for data fetching. Supabase Realtime WebSockets are not aggressively pushing state updates to the browser. 
As a result, a "polling/refresh fallback" is currently required for cross-browser synchronization in the marketplace.

### Findings
- **Order Synchronization**: Customer creates order -> Merchant must refresh to see new order -> Partner must refresh to see accepted job.
- **RLS Limitation**: The `orders` table lacks a `SELECT` policy for admins, meaning the Admin Dashboard does not sync Realtime events correctly without RLS bypass.
- **Status Events**: We verified status transitions work on the backend (pending -> accepted -> picked_up -> delivered).

### Implemented Fallback
To ensure 100% reliability during the end-to-end browser flow validation, we have implemented React-based polling fallbacks:

1. **Customer Order Tracker**: Polls every 5 seconds.
2. **Merchant Dashboard**: Polls every 10 seconds.
3. **Partner Jobs Board**: Polls every 5 seconds.
4. **Admin Command Center**: Added manual refresh buttons / heavily leverages `revalidatePath`.

This hybrid approach ensures that if WebSockets are unavailable or if Next.js router cache goes stale, the UI will forcefully reconcile with the database state at predictable intervals.

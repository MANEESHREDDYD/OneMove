/**
 * Shared accessibility constants.
 *
 * This module deliberately has no "use client" directive and imports nothing,
 * so both server components (app/layout.tsx) and client components
 * (components/layout/AppShell.tsx) can read the same value. Exporting it from
 * the "use client" AppShell module instead would turn it into a client
 * reference and make it unusable from the server layout.
 */

/**
 * The id of the single `<main>` landmark on every route. The skip link in
 * app/layout.tsx targets it, so exactly one element per rendered page must
 * carry this id — see AppShell (authenticated + auth routes) and app/page.tsx
 * (the landing page, which owns its own banner/main/contentinfo structure).
 */
export const MAIN_CONTENT_ID = "main-content"

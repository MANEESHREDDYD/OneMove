# OneMove Checkpoints

## Checkpoint 00: Repo Bootstrapping
- **Completed Work**: Initialized Next.js app, installed dependencies, configured docs.
- **Validation Commands Run**: `npm run lint` (using eslint directly), `npm run typecheck`, `npm run build`
- **Test Summary**: Successfully verified initialization, strict typing, and build output.
- **Bug Count Found**: 0
- **Bug Count Fixed**: 0
- **Final Push Status**: Pushed to main

## Checkpoint 01: Product Shell + Design System
- **Completed Work**: Created AppShell, responsive navigation, landing page, auth placeholders, dark theme layout, and common shadcn/ui components.
- **Validation Commands Run**: `npx eslint .`, `npm run typecheck`, `npm run build`
- **Test Summary**: Verified UI compilation and Next.js static prerendering.
- **Bug Count Found**: 2 (Unescaped entity in login, invalid Server Component onClick usage in page.tsx)
- **Bug Count Fixed**: 2
- **Final Push Status**: Pushed to main

## Checkpoint 02: Supabase Schema + Seed Data
- **Completed Work**: Installed Supabase SDKs, scaffolded initial config, wrote SQL schema with RLS and triggers, generated heavy realistic 5-city seed data script, setup database types and client utils.
- **Validation Commands Run**: `npm run typecheck`, `npm run build`, verified seed SQL generation.
- **Test Summary**: Types and components compile successfully with new dependencies.
- **Bug Count Found**: 1 (ts-node ESM compatibility issue)
- **Bug Count Fixed**: 1
- **Final Push Status**: Pushed to main

## Checkpoint 03: Auth + Role Routing
- **Completed Work**: Integrated Supabase Server Actions for Login/Register, implemented `/auth/callback`, configured `proxy.ts` (formerly `middleware.ts`) for strict SSR role-based route protection, created dashboard stubs for all 4 roles (`customer`, `driver`, `merchant`, `admin`), and added `00001_auth_trigger.sql` for auto-profile generation.
- **Validation Commands Run**: `npx eslint .`, `npm run typecheck`, `npm run build`
- **Test Summary**: Verified auth action typings, middleware routing logic, and layout resolution.
- **Bug Count Found**: 2 (ESLint unused vars warning, Next.js 16 deprecated middleware file convention)
- **Bug Count Fixed**: 2 (Removed unused variable, renamed `middleware.ts` to `proxy.ts`)
- **Final Push Status**: Pushed to main

## Checkpoint 04: Customer Super-App Dashboard
- **Completed Work**: Completely rewrote `ServiceCard` to support premium ReactNode icons, hover scaling, and dynamic gradient injection. Scaffolded core routes (`/customer/rides`, `/customer/eats`, `/customer/grocery`, `/customer/orders`). Developed `/customer/page.tsx` with a secure server-action based Supabase call to fetch and render active `orders` for the logged-in customer directly on the dashboard.
- **Validation Commands Run**: `npx eslint .`, `npm run typecheck`, `npm run build`
- **Test Summary**: Build succeeded. Addressed strict TypeScript object schema boundaries for arbitrary JSON outputs.
- **Bug Count Found**: 1 (TypeScript schema typing warning accessing `.address` on Supabase's generated Json utility type).
- **Bug Count Fixed**: 1 (Added strict cast assertions to interpret generic JSON fields as mapped `address` objects).
- **Final Push Status**: Pushed to main

## Checkpoint 05: Rides Marketplace Vertical
- **Completed Work**: Developed `utils/pricing.ts` as a mock utility engine to calculate pseudo-random distances and dynamic surge multipliers. Created `RideBookingForm.tsx` as a Client Component utilizing state tracking for live price estimation. Developed the server action `actions.ts` to execute secure backend database inserts into the `orders` table. Updated `app/customer/rides/page.tsx` to host the form.
- **Validation Commands Run**: `npx eslint .`, `npm run typecheck`, `npm run build`
- **Test Summary**: React Client Components, Effects, and Server Action typings successfully align.
- **Bug Count Found**: 2 (React state mutation warning inside `useEffect`, Next.js 15 strict server action inline return typing constraint).
- **Bug Count Fixed**: 2 (Migrated dynamic calculation out of the effect lifecycle natively into the pure render phase, decoupled form action to an async wrapper function).
- **Final Push Status**: Pushed to main

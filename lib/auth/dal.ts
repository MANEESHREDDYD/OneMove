import { cache } from 'react'
import { redirect } from 'next/navigation'
import { createClient } from '@/utils/supabase/server'
import { roleHomePath, type AppRole } from '@/lib/auth/roles'

/**
 * Central server-side Data Access Layer for authorization.
 *
 * Next.js 16 guidance (node_modules/next/dist/docs/01-app/02-guides/authentication.md):
 * Proxy (formerly Middleware) is only an *optimistic* check and must not be the
 * sole line of defense. The authoritative check belongs as close to the data as
 * possible, so every protected Server Component calls into this module.
 *
 * Role is stored in the `profiles.role` column, matching the pre-existing checks in
 * app/admin/command-center/page.tsx and app/admin/system-health/page.tsx.
 */

export { roleHomePath }
export type { AppRole }

export type AdminSession = {
  userId: string
  role: 'admin'
}

type SessionProfile =
  | { configured: false }
  | { configured: true; user: { id: string } | null; role: string | null }

/**
 * Resolves the current user and their persisted role.
 * Memoized per render pass with React `cache` so repeated calls within one
 * request do not re-query Supabase.
 */
export const getSessionProfile = cache(async (): Promise<SessionProfile> => {
  const supabase = await createClient()

  // Supabase env not configured: the caller renders a setup screen instead.
  if (!supabase) {
    return { configured: false }
  }

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    return { configured: true, user: null, role: null }
  }

  const { data: profile } = await supabase
    .from('profiles')
    .select('role')
    .eq('id', user.id)
    .single()

  return {
    configured: true,
    user: { id: user.id },
    role: (profile?.role as string | undefined) ?? null,
  }
})

/**
 * Authoritative admin gate. Call at the top of every `/admin/**` Server Component.
 *
 * - Unauthenticated  -> redirect to /auth/login
 * - Authenticated but not `role === 'admin'` -> redirect to their own dashboard
 *   (fail-closed: a missing profile row is treated as non-admin)
 * - Supabase not configured -> returns `null` so the caller renders <SetupRequired />
 */
export const requireAdmin = cache(async (): Promise<AdminSession | null> => {
  const session = await getSessionProfile()

  if (!session.configured) {
    return null
  }

  if (!session.user) {
    redirect('/auth/login')
  }

  if (session.role !== 'admin') {
    redirect(roleHomePath(session.role))
  }

  return { userId: session.user.id, role: 'admin' }
})

export type AdminGuardResult =
  | { ok: true; userId: string }
  | { ok: false; status: 401 | 403 | 503; error: string }

/**
 * Non-redirecting admin gate for Server Actions and Route Handlers.
 *
 * Server Actions and Route Handlers are independently addressable HTTP endpoints:
 * a guard on the page that renders the form does NOT protect them, and neither does
 * the optimistic check in `proxy.ts` alone. Every mutating admin endpoint must call
 * this and refuse on `ok: false`.
 */
export async function requireAdminApi(): Promise<AdminGuardResult> {
  const session = await getSessionProfile()

  if (!session.configured) {
    return { ok: false, status: 503, error: 'Supabase setup required' }
  }

  if (!session.user) {
    return { ok: false, status: 401, error: 'Unauthorized' }
  }

  if (session.role !== 'admin') {
    return { ok: false, status: 403, error: 'Forbidden' }
  }

  return { ok: true, userId: session.user.id }
}

/**
 * Role constants and route mapping.
 *
 * Deliberately free of `next/headers`, `next/navigation`, and Supabase imports so it
 * can be shared by the root `proxy.ts` (request scope) and the Server Component DAL.
 *
 * Roles are persisted in the `profiles.role` column.
 */

export type AppRole = 'admin' | 'customer' | 'driver' | 'merchant'

/**
 * Maps a `profiles.role` value to the dashboard route that role owns.
 * Unknown or missing roles fall back to the least-privileged dashboard.
 */
export function roleHomePath(role: string | null | undefined): string {
  switch (role) {
    case 'admin':
      return '/admin/command-center'
    case 'driver':
      return '/partner'
    case 'merchant':
      return '/merchant'
    default:
      return '/customer'
  }
}

import { createServerClient } from '@supabase/ssr'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { roleHomePath } from '@/lib/auth/roles'

/**
 * Next.js 16 renamed the `middleware` file convention to `proxy`
 * (node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/middleware.md:
 * "The `middleware.js` file convention has been deprecated in Next.js 16 and renamed to
 * `proxy.js`"). A root `middleware.ts` would be dead code in this version, so the
 * request-level gate lives here.
 *
 * This is an OPTIMISTIC check only. Per the Next.js authentication guide, Proxy
 * "should not be your only line of defense"; the authoritative admin check is
 * `requireAdmin()` from `@/lib/auth/dal`, invoked by every /admin/** Server Component.
 */

/** Route prefixes that require an authenticated session. */
const PROTECTED_PREFIXES = ['/customer', '/admin', '/merchant', '/partner', '/executive']

/** Route prefixes that require `profiles.role === 'admin'`. */
const ADMIN_ONLY_PREFIXES = ['/admin', '/executive']

export async function proxy(request: NextRequest) {
  const response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  })

  response.headers.set('Cache-Control', 'no-store, max-age=0')

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!supabaseUrl || !supabaseAnonKey) {
    return response
  }

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll()
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value, options }) => {
          request.cookies.set(name, value)
          response.cookies.set(name, value, options)
        })
      },
    },
  })

  const {
    data: { user },
  } = await supabase.auth.getUser()

  const pathname = request.nextUrl.pathname
  const isAuthRoute = pathname.startsWith('/auth')
  const isProtected = PROTECTED_PREFIXES.some((path) => pathname.startsWith(path))
  const isAdminOnly = ADMIN_ONLY_PREFIXES.some((path) => pathname.startsWith(path))

  if (isProtected && !user) {
    return NextResponse.redirect(new URL('/auth/login', request.url))
  }

  if (user && (isAdminOnly || isAuthRoute)) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', user.id)
      .single()

    const role = (profile?.role as string | undefined) ?? null

    // Fail closed: anything that is not an explicit 'admin' role is bounced to
    // the dashboard that role owns.
    if (isAdminOnly && role !== 'admin') {
      return NextResponse.redirect(new URL(roleHomePath(role), request.url))
    }

    if (isAuthRoute) {
      return NextResponse.redirect(new URL(roleHomePath(role), request.url))
    }
  }

  return response
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}

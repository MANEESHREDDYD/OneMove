import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'
import { hasSupabaseConfig, getMissingEnvMessage } from '@/utils/env'

export async function updateSession(request: NextRequest) {
  // Guard: If Supabase is not configured, skip all auth logic and let the
  // request proceed to the page which will show a setup-required screen.
  if (!hasSupabaseConfig()) {
    console.warn(getMissingEnvMessage())
    return NextResponse.next({ request })
  }

  let supabaseResponse = NextResponse.next({
    request,
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value))
          supabaseResponse = NextResponse.next({
            request,
          })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  const {
    data: { user },
  } = await supabase.auth.getUser()

  // Protect dashboard routes
  const isAuthRoute = request.nextUrl.pathname.startsWith('/auth')
  const isProtectedRoute = 
    request.nextUrl.pathname.startsWith('/customer') ||
    request.nextUrl.pathname.startsWith('/partner') ||
    request.nextUrl.pathname.startsWith('/merchant') ||
    request.nextUrl.pathname.startsWith('/admin')

  if (!user && isProtectedRoute) {
    const url = request.nextUrl.clone()
    url.pathname = '/auth/login'
    return NextResponse.redirect(url)
  }

  // If user is logged in, fetch their role to ensure they are on the correct dashboard
  if (user && isProtectedRoute) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', user.id)
      .single()

    const role = profile?.role || 'customer'
    const routePrefix = role === 'driver' ? 'partner' : role
    
    // Check if trying to access a route for a different role
    if (request.nextUrl.pathname.startsWith('/partner') && role !== 'driver' && role !== 'admin') {
      const url = request.nextUrl.clone()
      url.pathname = `/${routePrefix}`
      return NextResponse.redirect(url)
    }
    if (request.nextUrl.pathname.startsWith('/merchant') && role !== 'merchant' && role !== 'admin') {
      const url = request.nextUrl.clone()
      url.pathname = `/${routePrefix}`
      return NextResponse.redirect(url)
    }
    if (request.nextUrl.pathname.startsWith('/admin') && role !== 'admin') {
      const url = request.nextUrl.clone()
      url.pathname = `/${routePrefix}`
      return NextResponse.redirect(url)
    }
  }

  // If logged in and trying to access auth pages, redirect to dashboard
  if (user && isAuthRoute) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', user.id)
      .single()
    
    const role = profile?.role || 'customer'
    const routePrefix = role === 'driver' ? 'partner' : role
    const url = request.nextUrl.clone()
    url.pathname = role === 'admin' ? '/admin/command-center' : `/${routePrefix}`
    return NextResponse.redirect(url)
  }

  return supabaseResponse
}

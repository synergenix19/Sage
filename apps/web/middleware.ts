import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'
import { TOTAL_ONBOARDING_STEPS } from '@/lib/onboarding-constants'
import { can } from '@/lib/auth/edge-permissions'
import type { RoleKey } from '@/lib/auth/edge-permissions'

const AUTH_PATHS = ['/sign-in', '/sign-up', '/forgot-password', '/auth/callback', '/reset-password']

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const response = NextResponse.next({ request })

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!supabaseUrl || !supabaseKey) {
    throw new Error('[middleware] NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set')
  }

  const supabase = createServerClient(
    supabaseUrl,
    supabaseKey,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (toSet) => toSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options)
        ),
      },
    }
  )

  const { data: { user } } = await supabase.auth.getUser()

  // Unauthenticated → sign-in (skip auth routes themselves)
  if (!user) {
    if (pathname.startsWith('/api/')) {
      return new NextResponse(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    if (!AUTH_PATHS.some(p => pathname.startsWith(p))) {
      return NextResponse.redirect(new URL('/sign-in', request.url))
    }
  }

  // Root redirect
  if (user && pathname === '/') {
    return NextResponse.redirect(new URL('/chat', request.url))
  }

  if (user && !AUTH_PATHS.some(p => pathname.startsWith(p)) && pathname !== '/') {
    const tenantId = process.env.NEXT_PUBLIC_TENANT_ID
    if (!tenantId) {
      // Config error — redirect cleanly rather than 500 on every request.
      // Fix: set NEXT_PUBLIC_TENANT_ID in all environments.
      console.error('[middleware] NEXT_PUBLIC_TENANT_ID not set')
      return NextResponse.redirect(new URL('/sign-in', request.url))
    }

    const { data: roleData } = await supabase
      .from('v_user_roles_for_tenant')
      .select('roles')
      .eq('user_id', user.id)
      .eq('tenant_id', tenantId)
      .maybeSingle()

    const roles = (roleData?.roles as RoleKey[]) ?? ['member']

    // Middleware enforces two distinct staff access layers before the request reaches RSC.
    // This is defense-in-depth: middleware PLUS the layout's requireCapability() both gate access.
    // See: CVE-2025-29927 — middleware can be bypassed via x-middleware-subrequest header
    // (patched in Next.js 15.5.18 installed here, but the layout is the authoritative gate).
    //
    // Layer 1 — staff:access gate (redirects to /sign-in: user has no staff role at all)
    if (pathname.startsWith('/admin') || pathname.startsWith('/live')) {
      if (!can(roles, 'staff:access')) {
        return NextResponse.redirect(new URL('/sign-in', request.url))
      }
    }
    // Layer 2 — surface-specific gate (rewrite to /_not-found: authenticated staff on wrong surface)
    // Redirecting to /sign-in here would be wrong — the user IS authenticated, just on the
    // wrong surface. A 404 is the correct response (capability non-disclosure, per S-1).
    // We use NextResponse.rewrite() to /_not-found so:
    //   a) The URL stays at /live or /admin (no misleading redirect to /sign-in)
    //   b) The response is issued by middleware before RSC streaming begins → HTTP 404
    //   c) Layout never runs → no streaming-order status-code issue
    if (pathname.startsWith('/live') && !can(roles, 'live:read')) {
      const notFoundUrl = request.nextUrl.clone()
      notFoundUrl.pathname = '/_not-found'
      return NextResponse.rewrite(notFoundUrl, { status: 404 })
    }
    if (pathname.startsWith('/admin') && !can(roles, 'admin:read')) {
      const notFoundUrl = request.nextUrl.clone()
      notFoundUrl.pathname = '/_not-found'
      return NextResponse.rewrite(notFoundUrl, { status: 404 })
    }

    // Onboarding gate — staff bypass is intentional (staff users don't need a member profile).
    // Non-staff authenticated users on protected routes make two Supabase queries total:
    // the role lookup above and this onboarding profile fetch. Acceptable pre-Gitex;
    // cache resolved roles as a signed session claim post-Gitex to eliminate the second query.
    const isStaff = can(roles, 'staff:access')
    const isOnboardingStep = new RegExp(`^/step-[1-${TOTAL_ONBOARDING_STEPS}]$`).test(pathname)

    if (!isStaff && !isOnboardingStep) {
      const { data: profile } = await supabase
        .from('user_profiles')
        .select('onboarding_complete, onboarding_step')
        .eq('id', user.id)
        .maybeSingle()
      if (!profile || !profile.onboarding_complete) {
        const step = profile?.onboarding_step
        const target = step && step > 0 ? `/step-${step}` : '/step-1'
        return NextResponse.redirect(new URL(target, request.url))
      }
    }
  }

  return response
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|icons|manifest.json|offline.html|sw\\.js).*)'],
}

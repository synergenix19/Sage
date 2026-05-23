import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

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

  // Single profile fetch — used for both admin check and onboarding gate.
  // Never make two round-trips to Supabase per middleware call.
  if (user && !AUTH_PATHS.some(p => pathname.startsWith(p)) && pathname !== '/') {
    const { data: profile } = await supabase
      .from('user_profiles')
      .select('is_admin, onboarding_complete, onboarding_step')
      .eq('id', user.id)
      .single()

    if (pathname.startsWith('/admin') && !profile?.is_admin) {
      return new NextResponse(null, { status: 403 })
    }

    const isOnboardingStep = /^\/step-[1-6]$/.test(pathname)
    const needsOnboarding = !profile || !profile.onboarding_complete
    if (!pathname.startsWith('/admin') && !isOnboardingStep && needsOnboarding) {
      const step = profile?.onboarding_step
      const target = step && step > 0 ? `/step-${step}` : '/step-1'
      return NextResponse.redirect(new URL(target, request.url))
    }
  }

  return response
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|icons|manifest.json|offline.html|sw\\.js).*)'],
}

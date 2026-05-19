import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

const AUTH_PATHS = ['/sign-in', '/sign-up', '/forgot-password']

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const response = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (toSet) => toSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options)
        ),
      },
    }
  )

  const { data: { session } } = await supabase.auth.getSession()

  // Unauthenticated → sign-in (skip auth routes themselves)
  if (!session && !AUTH_PATHS.some(p => pathname.startsWith(p))) {
    return NextResponse.redirect(new URL('/sign-in', request.url))
  }

  // Root redirect
  if (session && pathname === '/') {
    return NextResponse.redirect(new URL('/chat', request.url))
  }

  // Single profile fetch — used for both admin check and onboarding gate.
  // Never make two round-trips to Supabase per middleware call.
  if (session && !AUTH_PATHS.some(p => pathname.startsWith(p)) && pathname !== '/') {
    const { data: profile } = await supabase
      .from('user_profiles')
      .select('is_admin, onboarding_complete, onboarding_step')
      .eq('id', session.user.id)
      .single()

    if (pathname.startsWith('/admin') && !profile?.is_admin) {
      return new NextResponse(null, { status: 403 })
    }

    if (
      !pathname.startsWith('/admin') &&
      !pathname.startsWith('/onboarding') &&
      profile && !profile.onboarding_complete
    ) {
      return NextResponse.redirect(
        new URL(`/onboarding/step-${profile.onboarding_step}`, request.url)
      )
    }
  }

  return response
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|icons|manifest.json|offline.html).*)'],
}

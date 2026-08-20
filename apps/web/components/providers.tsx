'use client'
import { useRef } from 'react'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { useTextSizeStore } from '@/lib/stores/text-size-store'
import { cn } from '@cdai/ui'
import type { Locale } from '@cdai/types'

interface ProvidersProps {
  children: React.ReactNode
  initialLocale: Locale
}

export function Providers({ children, initialLocale }: ProvidersProps) {
  const textSize = useTextSizeStore((s) => s.size)

  // Seed the locale store from the server-read cookie (layout.tsx), once, on
  // first render. Locale changes after mount always go through setLocale,
  // which triggers a hard reload/navigation — so this never needs to run
  // again for the lifetime of this mount, and must not re-force the initial
  // value on later re-renders (e.g. a text-size change) or it would stomp a
  // pending locale change before the reload takes effect.
  //
  // INVARIANT (enforced by test, not by tree position alone — see
  // providers.test.tsx): Providers is the sole seeder of useLocaleStore, and
  // no locale-subscribing component may mount above Providers in the app
  // tree. This setState-in-render-body is only safe because nothing above
  // this point has subscribed yet; a subscriber mounted higher would render
  // once against the store's un-seeded default before this line runs.
  // Rejected alternatives: a useLayoutEffect seed would leave every
  // subscriber's first render (and the full SSR pass, which never executes
  // effects) using the store's default locale instead of the server-read
  // cookie — a guaranteed locale flash, not a hydration nuance. A per-request
  // store via React context would remove the render-body write, but every
  // `useLocaleStore` call site would need to become a context hook,
  // including crisis-card.tsx, crisis-resource-list.tsx, and chat-header.tsx
  // — files Amendment 7 (CRISIS-UI RULE) forbids editing for i18n
  // unification. Do not "fix" this without re-reading both rejections.
  const seeded = useRef(false)
  if (!seeded.current) {
    useLocaleStore.setState({ locale: initialLocale })
    seeded.current = true
  }

  // TODO(post-Gitex): Replace [&_*] descendant selector with CSS custom property
  // --text-scale approach to avoid Tailwind specificity conflicts.
  return (
    <div className={cn(
      textSize === 'sm' && '[&_*]:text-[0.875em]',
      textSize === 'lg' && '[&_*]:text-[1.125em]'
    )}>
      {children}
    </div>
  )
}

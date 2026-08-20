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

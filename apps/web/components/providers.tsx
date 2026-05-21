'use client'
import { useEffect } from 'react'
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

  useEffect(() => {
    // Hydrate store from server-read cookie on first mount only
    useLocaleStore.setState({ locale: initialLocale })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

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

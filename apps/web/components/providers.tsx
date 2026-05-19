'use client'
import { useEffect } from 'react'
import { useLocaleStore } from '@/lib/stores/locale-store'
import type { Locale } from '@cdai/types'

interface ProvidersProps {
  children: React.ReactNode
  initialLocale: Locale
}

export function Providers({ children, initialLocale }: ProvidersProps) {
  useEffect(() => {
    // Hydrate store from server-read cookie on first mount only
    useLocaleStore.setState({ locale: initialLocale })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return <>{children}</>
}

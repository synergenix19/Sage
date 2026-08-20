'use client'
import { useEffect } from 'react'
import { ErrorFallback } from '@/components/error-fallback'

export default function AppErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return <ErrorFallback reset={reset} className="h-full" />
}

import type { Locale } from '@cdai/types'

export function formatRelativeTime(updatedAt: string, locale: Locale = 'en'): string {
  const now = Date.now()
  const then = new Date(updatedAt).getTime()
  const diffMs = now - then
  const diffMins = Math.floor(diffMs / 60_000)
  const diffHours = Math.floor(diffMs / 3_600_000)

  if (diffHours < 1) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`

  const nowDate = new Date(now)
  const thenDate = new Date(then)

  const yesterday = new Date(nowDate)
  yesterday.setDate(nowDate.getDate() - 1)
  if (
    thenDate.getFullYear() === yesterday.getFullYear() &&
    thenDate.getMonth() === yesterday.getMonth() &&
    thenDate.getDate() === yesterday.getDate()
  ) {
    return 'Yesterday'
  }

  const displayLocale = locale === 'ar' ? 'ar-AE' : 'en-US'
  const diffDays = Math.floor(diffMs / 86_400_000)
  if (diffDays < 7) {
    return thenDate.toLocaleDateString(displayLocale, { weekday: 'long' })
  }

  return thenDate.toLocaleDateString(displayLocale, { month: 'short', day: 'numeric' })
}

'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@cdai/ui'
import { tenant } from '@cdai/tenant'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { t } from '@/lib/copy'
import { isActiveHref, navItemClass } from '@/lib/nav-active'

// label/labelAr moved to lib/copy.ts under tabBar.chat / tabBar.progress / tabBar.biomarker —
// `id` is the lookup key both TabBar and AppSideNav use against that registry.
export const ALL_TABS = [
  { href: '/chat', id: 'chat' as const },
  { href: '/progress', id: 'progress' as const },
  ...(tenant.capabilities.voiceBiomarker
    ? [{ href: '/biomarker', id: 'biomarker' as const }]
    : []),
]

export function TabBar({ className }: { className?: string }) {
  const pathname = usePathname()
  const locale = useLocaleStore((s) => s.locale)
  return (
    <nav className={cn('border-t border-[var(--color-border)] bg-[var(--color-surface)] flex pb-[env(safe-area-inset-bottom)]', className)}>
      {ALL_TABS.map((tab) => {
        const active = isActiveHref(pathname, tab.href)
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              'flex flex-1 flex-col items-center justify-center py-3 text-xs transition-colors duration-200 min-h-[44px]',
              navItemClass(active, 'text-[var(--color-primary)] font-medium', 'text-[var(--color-text-secondary)]')
            )}
          >
            <span>{t(`tabBar.${tab.id}`, locale)}</span>
            {active && <span className="mt-0.5 h-0.5 w-4 rounded-full bg-[var(--color-primary)]" />}
          </Link>
        )
      })}
    </nav>
  )
}

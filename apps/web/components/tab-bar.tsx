'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@cdai/ui'
import { tenant } from '@cdai/tenant'
import { useLocaleStore } from '@/lib/stores/locale-store'

export const ALL_TABS = [
  { href: '/chat', label: 'Chat', labelAr: 'محادثة' },
  { href: '/progress', label: 'Progress', labelAr: 'تقدمي' },
  ...(tenant.capabilities.voiceBiomarker
    ? [{ href: '/biomarker', label: 'Voice', labelAr: 'صوت' }]
    : []),
]

export function TabBar({ className }: { className?: string }) {
  const pathname = usePathname()
  const locale = useLocaleStore((s) => s.locale)
  return (
    <nav className={cn('border-t border-[var(--color-border)] bg-[var(--color-surface)] flex', className)}>
      {ALL_TABS.map((tab) => {
        const active = pathname.startsWith(tab.href)
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              'flex flex-1 flex-col items-center justify-center py-3 text-xs transition-colors duration-200 min-h-[44px]',
              active
                ? 'text-[var(--color-primary)] font-medium'
                : 'text-[var(--color-text-secondary)]'
            )}
          >
            <span>{locale === 'ar' ? tab.labelAr : tab.label}</span>
            {active && <span className="mt-0.5 h-0.5 w-4 rounded-full bg-[var(--color-primary)]" />}
          </Link>
        )
      })}
    </nav>
  )
}

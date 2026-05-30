'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { cn } from '@cdai/ui'
import { tenant } from '@cdai/tenant'
import { useCan } from '@/lib/auth/use-can'
import { signOutUser } from '@/lib/auth-actions'

const NAV_ITEMS = [
  { href: '/live',  label: 'Live',  capability: 'live:read'  },
  { href: '/admin', label: 'Admin', capability: 'admin:read' },
] as const

export function StaffNav() {
  const pathname = usePathname()
  const router = useRouter()
  const userCan = useCan()

  const visibleItems = NAV_ITEMS.filter((item) => userCan(item.capability))

  return (
    <header className="flex h-12 flex-shrink-0 items-center gap-3 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4">
      <span className="text-sm font-semibold text-[var(--color-text-primary)] me-2" aria-hidden="true">
        {tenant.copy.appName}
      </span>

      <nav aria-label="Staff navigation" className="flex items-center gap-1 flex-1">
        {visibleItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            aria-current={pathname.startsWith(item.href) ? 'page' : undefined}
            className={cn(
              'flex h-8 items-center rounded-lg px-3 text-sm font-medium transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring-color)]',
              pathname.startsWith(item.href)
                ? 'bg-[var(--color-primary)] text-white'
                : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]'
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <button
        onClick={() => signOutUser(router.push)}
        aria-label="Sign out"
        className={cn(
          'flex h-8 items-center rounded-lg px-3 text-sm font-medium transition-colors',
          'text-[var(--color-text-secondary)] hover:text-[var(--color-crisis)] hover:bg-[var(--color-surface-tinted)]',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring-color)]'
        )}
      >
        Sign out
      </button>
    </header>
  )
}

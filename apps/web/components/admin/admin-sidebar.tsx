'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@cdai/ui'
import { tenant } from '@cdai/tenant'

const NAV_LINKS = [
  { href: '/admin', label: 'Dashboard', exact: true },
  { href: '/admin/users', label: 'Users', exact: false },
  { href: '/admin/settings', label: 'Settings', exact: false },
]

export function AdminSidebar() {
  const pathname = usePathname()

  return (
    <aside className="bg-[var(--color-surface)] border-e border-[var(--color-border)] w-60 flex-shrink-0 flex flex-col p-4 gap-1">
      <div className="mb-4 ps-2">
        <span className="text-sm font-semibold text-[var(--color-text-primary)]">
          {tenant.copy.appName}
        </span>
        <p className="text-xs text-[var(--color-text-secondary)]">Admin</p>
      </div>
      <nav className="flex flex-col gap-1">
        {NAV_LINKS.map((link) => {
          const active = link.exact ? pathname === link.href : pathname.startsWith(link.href)
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                'flex min-h-11 items-center rounded-xl px-3 py-2 text-sm font-medium transition-colors duration-150',
                active
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]'
              )}
            >
              {link.label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}

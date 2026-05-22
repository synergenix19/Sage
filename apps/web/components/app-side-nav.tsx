'use client'
import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { cn } from '@cdai/ui'
import { tenant } from '@cdai/tenant'
import { LanguageToggle } from '@/components/auth/language-toggle'
import { ALL_TABS } from '@/components/tab-bar'
import { useLocaleStore } from '@/lib/stores/locale-store'
import { createClient } from '@/lib/supabase/client'
import { signOutUser } from '@/lib/auth-actions'

export function AppSideNav() {
  const pathname = usePathname()
  const router = useRouter()
  const locale = useLocaleStore((s) => s.locale)
  const [email, setEmail] = useState<string | null>(null)
  const [showConfirm, setShowConfirm] = useState(false)
  const cancelRef = useRef<HTMLButtonElement>(null)
  const signOutConfirmRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    createClient()
      .auth.getUser()
      .then(({ data }) => setEmail(data.user?.email ?? null))
  }, [])

  useEffect(() => {
    if (showConfirm) cancelRef.current?.focus()
  }, [showConfirm])

  function handleDialogKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') {
      setShowConfirm(false)
      return
    }
    if (e.key === 'Tab') {
      e.preventDefault()
      const active = document.activeElement
      if (!e.shiftKey) {
        if (active === cancelRef.current) signOutConfirmRef.current?.focus()
        else cancelRef.current?.focus()
      } else {
        if (active === signOutConfirmRef.current) cancelRef.current?.focus()
        else signOutConfirmRef.current?.focus()
      }
    }
  }

  const confirmText =
    locale === 'ar'
      ? 'تسجيل الخروج من Sage؟ سيتم حفظ تاريخ محادثاتك.'
      : 'Sign out of Sage? Your conversation history is saved.'

  return (
    <aside className="hidden md:flex flex-col w-60 flex-shrink-0 bg-[var(--color-surface)] border-e border-[var(--color-border)]">
      {/* Brand */}
      <div className="px-4 py-5">
        <span className="text-sm font-semibold text-[var(--color-text-primary)]">
          {tenant.copy.appName}
        </span>
      </div>

      {/* Nav links */}
      <nav className="flex flex-col gap-1 px-3">
        {ALL_TABS.map((tab) => {
          const active = pathname.startsWith(tab.href)
          const label = locale === 'ar' ? tab.labelAr : tab.label
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                'flex min-h-[44px] items-center rounded-xl px-3 py-2 text-sm font-medium transition-colors duration-150',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring-color)] focus-visible:ring-offset-2',
                active
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)]'
              )}
            >
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Footer */}
      <div className="border-t border-[var(--color-border)] p-3 flex flex-col gap-3">
        <LanguageToggle />

        <div className="border-t border-[var(--color-border)] pt-3">
          {!showConfirm ? (
            <div className="flex items-center gap-2 min-h-[44px] px-1">
              {/* Avatar */}
              <div
                aria-hidden="true"
                className="h-7 w-7 rounded-full bg-[var(--color-primary-dark)] flex items-center justify-center flex-shrink-0"
              >
                <span className="text-xs font-medium text-white">
                  {email ? email.charAt(0).toUpperCase() : '·'}
                </span>
              </div>
              {/* Email */}
              <span className="flex-1 truncate text-xs text-[var(--color-text-secondary)]">
                {email ?? ''}
              </span>
              {/* Sign out trigger */}
              <button
                onClick={() => setShowConfirm(true)}
                aria-label={locale === 'ar' ? 'تسجيل الخروج' : 'Sign out'}
                className={cn(
                  'p-1.5 rounded-lg text-[var(--color-text-secondary)] transition-colors',
                  'hover:text-[var(--color-crisis)] hover:bg-[var(--color-surface-tinted)]',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring-color)]'
                )}
              >
                {/* Log-out arrow icon */}
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <path
                    d="M6 14H3a1 1 0 0 1-1-1V3a1 1 0 0 1 1-1h3M11 11l3-3-3-3M14 8H6"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </div>
          ) : (
            <div
              role="dialog"
              aria-modal="true"
              aria-label={locale === 'ar' ? 'تأكيد تسجيل الخروج' : 'Confirm sign out'}
              onKeyDown={handleDialogKeyDown}
              className="flex flex-col gap-2"
            >
              <p className="text-xs text-[var(--color-text-secondary)] px-1">{confirmText}</p>
              <div className="flex gap-2">
                <button
                  ref={cancelRef}
                  onClick={() => setShowConfirm(false)}
                  className={cn(
                    'flex-1 rounded-xl border border-[var(--color-border)] py-2 text-xs font-medium',
                    'text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-tinted)] transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring-color)]'
                  )}
                >
                  {locale === 'ar' ? 'إلغاء' : 'Cancel'}
                </button>
                <button
                  ref={signOutConfirmRef}
                  onClick={() => signOutUser(router.push)}
                  className={cn(
                    'flex-1 rounded-xl border border-[var(--color-crisis)] py-2 text-xs font-medium',
                    'text-[var(--color-crisis)] hover:bg-red-50 transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-crisis)]'
                  )}
                >
                  {locale === 'ar' ? 'تسجيل الخروج' : 'Sign out'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  )
}

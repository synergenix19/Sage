import { LanguageToggle } from '@/components/auth/language-toggle'

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh flex flex-col items-center justify-center bg-[var(--color-surface)] px-4">
      <div className="absolute top-4 end-4">
        <LanguageToggle />
      </div>
      <div id="main-content" className="w-full max-w-sm">{children}</div>
    </div>
  )
}

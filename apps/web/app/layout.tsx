import type { Metadata } from 'next'
import { Plus_Jakarta_Sans, IBM_Plex_Sans_Arabic } from 'next/font/google'
import { cookies } from 'next/headers'
import { cssVarsString } from '@cdai/theme'
import { tenant } from '@cdai/tenant'
import { Providers } from '@/components/providers'
import { InstallPrompt } from '@/components/pwa/install-prompt'
import { SwUpdateBanner } from '@/components/pwa/sw-update-banner'
import type { Locale } from '@cdai/types'
import './globals.css'

const jakartaSans = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-body',
  display: 'swap',
})

const ibmPlexArabic = IBM_Plex_Sans_Arabic({
  subsets: ['arabic'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-arabic',
  display: 'swap',
})

export const metadata: Metadata = {
  title: tenant.copy.appName,
  description: tenant.copy.tagline,
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: tenant.copy.appName,
  },
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies()
  const locale = (cookieStore.get('cdai-locale')?.value ?? 'en') as Locale
  const dir = locale === 'ar' ? 'rtl' : 'ltr'
  const cssVars = cssVarsString(tenant.brand)

  return (
    <html lang={locale} dir={dir} className={locale === 'ar' ? ibmPlexArabic.variable : jakartaSans.variable}>
      <head>
        <style dangerouslySetInnerHTML={{ __html: cssVars }} />
        <link rel="apple-touch-icon" href="/icons/icon-180.png" />
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#F9F8F6" />
      </head>
      <body className="bg-[var(--color-surface)] text-[var(--color-text-primary)] font-body antialiased">
        <InstallPrompt />
        <SwUpdateBanner />
        <Providers initialLocale={locale}>{children}</Providers>
      </body>
    </html>
  )
}

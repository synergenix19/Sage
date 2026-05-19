import type { Metadata } from 'next'
import { Plus_Jakarta_Sans, IBM_Plex_Sans_Arabic } from 'next/font/google'
import { cookies } from 'next/headers'
import { cssVarsString } from '@cdai/theme'
import { tenant } from '@cdai/tenant'
import { Providers } from '@/components/providers'
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
  const fontClass = locale === 'ar' ? ibmPlexArabic.variable : jakartaSans.variable
  const cssVars = cssVarsString(tenant.brand)

  return (
    <html lang={locale} dir={dir} className={fontClass}>
      <head>
        <style dangerouslySetInnerHTML={{ __html: cssVars }} />
        <link rel="apple-touch-icon" href="/icons/icon-180.png" />
      </head>
      <body className="bg-[var(--color-surface)] text-[var(--color-text-primary)] antialiased">
        <Providers initialLocale={locale}>{children}</Providers>
      </body>
    </html>
  )
}

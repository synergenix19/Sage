import type { ReactNode } from 'react'
import { AppSideNav } from '@/components/app-side-nav'
import { TabBar } from '@/components/tab-bar'
import { OnboardingCleanup } from '@/components/onboarding-cleanup'

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-dvh flex-col md:flex-row">
      <OnboardingCleanup />
      <AppSideNav />
      <div className="mx-auto flex w-full max-w-md md:max-w-none md:flex-1 flex-col overflow-x-hidden">
        <main id="main-content" className="flex-1 overflow-hidden">{children}</main>
        <TabBar className="md:hidden" />
      </div>
    </div>
  )
}

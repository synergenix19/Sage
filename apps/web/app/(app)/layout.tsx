import type { ReactNode } from 'react'
import { TabBar } from '@/components/tab-bar'

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-dvh flex-col">
      <main className="flex-1 overflow-hidden">{children}</main>
      <TabBar />
    </div>
  )
}

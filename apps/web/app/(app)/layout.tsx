import type { ReactNode } from 'react'
import { TabBar } from '@/components/tab-bar'

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-dvh flex-col">
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col overflow-x-hidden">
        <main className="flex-1 overflow-hidden">{children}</main>
        <TabBar />
      </div>
    </div>
  )
}

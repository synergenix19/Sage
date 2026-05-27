import type { ReactNode } from 'react'

export const metadata = { title: 'Clinical Intelligence | SAGE' }

export default function LiveLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {children}
    </div>
  )
}

import type { ReactNode } from 'react'

export const metadata = { title: 'Clinical Intelligence | SAGE' }

export default function LiveRouteLayout({ children }: { children: ReactNode }) {
  return (
    <div
      className="min-h-full"
      style={{
        background: 'var(--color-clinical-surface, #0f172a)',
        color:      'var(--color-clinical-text, #f1f5f9)',
      }}
    >
      {children}
    </div>
  )
}

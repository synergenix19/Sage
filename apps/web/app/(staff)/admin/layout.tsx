import type { ReactNode } from 'react'
import { AdminSectionNav } from '@/components/admin/admin-section-nav'

export const metadata = { title: 'Admin | SAGE' }

export default function AdminRouteLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full">
      <AdminSectionNav />
      <div className="flex-1 overflow-y-auto p-6">{children}</div>
    </div>
  )
}
